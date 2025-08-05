"""Market microstructure with order books and matching engine."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
from sortedcontainers import SortedList
from pydantic import BaseModel, Field

from ..core.entity import Entity
from ..core.events import Event, EventBus
from ..core.resources import ResourceType
from ..world.engine import WorldSystem, SystemPriority


class OrderType(str, Enum):
    """Types of market orders."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    """Side of the order."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Status of an order."""
    PENDING = "pending"
    OPEN = "open"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class Order:
    """Market order."""
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""
    resource_type: ResourceType = ResourceType.GOLD
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.LIMIT
    quantity: float = 0.0
    price: Optional[float] = None
    stop_price: Optional[float] = None
    filled_quantity: float = 0.0
    average_fill_price: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def remaining_quantity(self) -> float:
        """Get remaining quantity to fill."""
        return self.quantity - self.filled_quantity
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.filled_quantity >= self.quantity
    
    @property
    def is_expired(self) -> bool:
        """Check if order has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def fill(self, quantity: float, price: float) -> float:
        """Fill order partially or completely."""
        fill_quantity = min(quantity, self.remaining_quantity)
        
        # Update average price
        total_value = self.average_fill_price * self.filled_quantity + price * fill_quantity
        self.filled_quantity += fill_quantity
        self.average_fill_price = total_value / self.filled_quantity if self.filled_quantity > 0 else price
        
        # Update status
        if self.is_filled:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIAL
        
        self.updated_at = time.time()
        return fill_quantity
    
    def cancel(self) -> None:
        """Cancel the order."""
        if self.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            return
        self.status = OrderStatus.CANCELLED
        self.updated_at = time.time()


class OrderBook:
    """Order book for a single resource type."""
    
    def __init__(self, resource_type: ResourceType):
        self.resource_type = resource_type
        
        # Sorted lists for price-time priority
        self.buy_orders: SortedList[Tuple[float, float, Order]] = SortedList(
            key=lambda x: (-x[0], x[1])  # Highest price first, then time
        )
        self.sell_orders: SortedList[Tuple[float, float, Order]] = SortedList(
            key=lambda x: (x[0], x[1])  # Lowest price first, then time
        )
        
        # Order lookup
        self.orders: Dict[str, Order] = {}
        
        # Market data
        self.last_price: Optional[float] = None
        self.last_quantity: Optional[float] = None
        self.last_trade_time: Optional[float] = None
        self.daily_volume: float = 0.0
        self.daily_high: Optional[float] = None
        self.daily_low: Optional[float] = None
    
    def add_order(self, order: Order) -> None:
        """Add order to the book."""
        if order.order_id in self.orders:
            return
        
        self.orders[order.order_id] = order
        order.status = OrderStatus.OPEN
        
        if order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY:
                self.buy_orders.add((order.price, order.created_at, order))
            else:
                self.sell_orders.add((order.price, order.created_at, order))
    
    def remove_order(self, order: Order) -> None:
        """Remove order from the book."""
        if order.order_id not in self.orders:
            return
        
        del self.orders[order.order_id]
        
        if order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY:
                self.buy_orders.remove((order.price, order.created_at, order))
            else:
                self.sell_orders.remove((order.price, order.created_at, order))
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        order = self.orders.get(order_id)
        if not order:
            return False
        
        order.cancel()
        self.remove_order(order)
        return True
    
    def get_best_bid(self) -> Optional[float]:
        """Get best bid price."""
        if self.buy_orders:
            return self.buy_orders[0][0]
        return None
    
    def get_best_ask(self) -> Optional[float]:
        """Get best ask price."""
        if self.sell_orders:
            return self.sell_orders[0][0]
        return None
    
    def get_spread(self) -> Optional[float]:
        """Get bid-ask spread."""
        bid = self.get_best_bid()
        ask = self.get_best_ask()
        if bid and ask:
            return ask - bid
        return None
    
    def get_mid_price(self) -> Optional[float]:
        """Get mid-market price."""
        bid = self.get_best_bid()
        ask = self.get_best_ask()
        if bid and ask:
            return (bid + ask) / 2
        return self.last_price
    
    def update_market_data(self, price: float, quantity: float) -> None:
        """Update market data after trade."""
        self.last_price = price
        self.last_quantity = quantity
        self.last_trade_time = time.time()
        self.daily_volume += quantity
        
        if self.daily_high is None or price > self.daily_high:
            self.daily_high = price
        if self.daily_low is None or price < self.daily_low:
            self.daily_low = price
    
    def get_depth(self, levels: int = 5) -> Dict[str, List[Tuple[float, float]]]:
        """Get order book depth."""
        bids = []
        asks = []
        
        # Aggregate by price level
        bid_levels = {}
        ask_levels = {}
        
        for price, _, order in self.buy_orders:
            if price not in bid_levels:
                bid_levels[price] = 0
            bid_levels[price] += order.remaining_quantity
        
        for price, _, order in self.sell_orders:
            if price not in ask_levels:
                ask_levels[price] = 0
            ask_levels[price] += order.remaining_quantity
        
        # Convert to sorted lists
        for price in sorted(bid_levels.keys(), reverse=True)[:levels]:
            bids.append((price, bid_levels[price]))
        
        for price in sorted(ask_levels.keys())[:levels]:
            asks.append((price, ask_levels[price]))
        
        return {"bids": bids, "asks": asks}


class Trade(BaseModel):
    """Executed trade."""
    trade_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    resource_type: ResourceType
    buy_order_id: str
    sell_order_id: str
    buyer_entity_id: str
    seller_entity_id: str
    price: float
    quantity: float
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MatchingEngine:
    """Order matching engine."""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.order_books: Dict[str, OrderBook] = {}
        self.trades: List[Trade] = []
        self.event_bus = event_bus
    
    def get_order_book(self, resource_type: ResourceType) -> OrderBook:
        """Get or create order book for resource."""
        if resource_type.value not in self.order_books:
            self.order_books[resource_type.value] = OrderBook(resource_type)
        return self.order_books[resource_type.value]
    
    def submit_order(self, order: Order) -> List[Trade]:
        """Submit order for matching."""
        book = self.get_order_book(order.resource_type)
        trades = []
        
        # Market orders
        if order.order_type == OrderType.MARKET:
            trades = self._match_market_order(order, book)
        
        # Limit orders
        elif order.order_type == OrderType.LIMIT:
            trades = self._match_limit_order(order, book)
        
        # Handle remaining quantity
        if not order.is_filled and order.order_type == OrderType.LIMIT:
            book.add_order(order)
        
        # Emit events
        if self.event_bus:
            for trade in trades:
                self.event_bus.emit(Event(
                    event_type="trade_executed",
                    data=trade.dict()
                ))
        
        return trades
    
    def _match_market_order(self, order: Order, book: OrderBook) -> List[Trade]:
        """Match market order against book."""
        trades = []
        
        if order.side == OrderSide.BUY:
            # Match against sell orders
            while order.remaining_quantity > 0 and book.sell_orders:
                price, created_at, counter_order = book.sell_orders[0]
                trades.extend(self._execute_trade(order, counter_order, price))
                
                if counter_order.is_filled:
                    book.remove_order(counter_order)
        else:
            # Match against buy orders
            while order.remaining_quantity > 0 and book.buy_orders:
                price, created_at, counter_order = book.buy_orders[0]
                trades.extend(self._execute_trade(counter_order, order, price))
                
                if counter_order.is_filled:
                    book.remove_order(counter_order)
        
        return trades
    
    def _match_limit_order(self, order: Order, book: OrderBook) -> List[Trade]:
        """Match limit order against book."""
        trades = []
        
        if order.side == OrderSide.BUY:
            # Match against sell orders at or below limit price
            while order.remaining_quantity > 0 and book.sell_orders:
                price, created_at, counter_order = book.sell_orders[0]
                
                if price > order.price:
                    break  # No more matches possible
                
                trades.extend(self._execute_trade(order, counter_order, price))
                
                if counter_order.is_filled:
                    book.remove_order(counter_order)
        else:
            # Match against buy orders at or above limit price
            while order.remaining_quantity > 0 and book.buy_orders:
                price, created_at, counter_order = book.buy_orders[0]
                
                if price < order.price:
                    break  # No more matches possible
                
                trades.extend(self._execute_trade(counter_order, order, price))
                
                if counter_order.is_filled:
                    book.remove_order(counter_order)
        
        return trades
    
    def _execute_trade(
        self,
        buy_order: Order,
        sell_order: Order,
        price: float
    ) -> List[Trade]:
        """Execute trade between two orders."""
        quantity = min(buy_order.remaining_quantity, sell_order.remaining_quantity)
        
        # Fill orders
        buy_order.fill(quantity, price)
        sell_order.fill(quantity, price)
        
        # Create trade record
        trade = Trade(
            resource_type=buy_order.resource_type,
            buy_order_id=buy_order.order_id,
            sell_order_id=sell_order.order_id,
            buyer_entity_id=buy_order.entity_id,
            seller_entity_id=sell_order.entity_id,
            price=price,
            quantity=quantity
        )
        
        self.trades.append(trade)
        
        # Update market data
        book = self.get_order_book(buy_order.resource_type)
        book.update_market_data(price, quantity)
        
        return [trade]
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        for book in self.order_books.values():
            if book.cancel_order(order_id):
                if self.event_bus:
                    self.event_bus.emit(Event(
                        event_type="order_cancelled",
                        data={"order_id": order_id}
                    ))
                return True
        return False
    
    def get_market_data(self, resource_type: ResourceType) -> Dict[str, Any]:
        """Get market data for resource."""
        book = self.get_order_book(resource_type)
        return {
            "resource": resource_type.value,
            "last_price": book.last_price,
            "bid": book.get_best_bid(),
            "ask": book.get_best_ask(),
            "spread": book.get_spread(),
            "mid_price": book.get_mid_price(),
            "volume": book.daily_volume,
            "high": book.daily_high,
            "low": book.daily_low,
            "depth": book.get_depth()
        }
    
    def get_trade_history(
        self,
        resource_type: Optional[ResourceType] = None,
        entity_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Trade]:
        """Get trade history with filters."""
        trades = self.trades[-limit:]
        
        if resource_type:
            trades = [t for t in trades if t.resource_type == resource_type]
        
        if entity_id:
            trades = [
                t for t in trades
                if t.buyer_entity_id == entity_id or t.seller_entity_id == entity_id
            ]
        
        return trades


class MarketSystem(WorldSystem):
    """System for market operations."""
    
    def __init__(self):
        super().__init__("MarketSystem", SystemPriority.NORMAL)
        self.matching_engine: Optional[MatchingEngine] = None
    
    async def initialize(self, world: World) -> None:
        """Initialize market system."""
        self.matching_engine = MatchingEngine(world.event_bus)
        
        # Register event handlers
        world.event_bus.register_handler(OrderEventHandler(self))
    
    async def update(self, world: World, delta_time: float) -> None:
        """Update market system."""
        # Process expired orders
        for book in self.matching_engine.order_books.values():
            expired_orders = []
            
            for order in book.orders.values():
                if order.is_expired:
                    expired_orders.append(order)
            
            for order in expired_orders:
                book.cancel_order(order.order_id)
                world.event_bus.emit(Event(
                    event_type="order_expired",
                    entity_id=order.entity_id,
                    data={"order_id": order.order_id}
                ))


class OrderEventHandler(EventHandler):
    """Handles order-related events."""
    
    def __init__(self, market_system: MarketSystem):
        super().__init__()
        self.market_system = market_system
        self.event_types = {"submit_order", "cancel_order"}
    
    async def handle(self, event: Event) -> Any:
        """Handle order events."""
        if event.event_type == "submit_order":
            order_data = event.data
            order = Order(
                entity_id=event.entity_id,
                resource_type=ResourceType(order_data["resource_type"]),
                side=OrderSide(order_data["side"]),
                order_type=OrderType(order_data.get("order_type", "limit")),
                quantity=order_data["quantity"],
                price=order_data.get("price"),
                expires_at=order_data.get("expires_at")
            )
            
            trades = self.market_system.matching_engine.submit_order(order)
            return {"order_id": order.order_id, "trades": trades}
        
        elif event.event_type == "cancel_order":
            order_id = event.data["order_id"]
            success = self.market_system.matching_engine.cancel_order(order_id)
            return {"success": success}