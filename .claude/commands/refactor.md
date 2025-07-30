# /refactor - Intelligent Code Refactoring

You are now in refactoring mode. Improve code quality systematically while maintaining functionality.

## Refactoring Strategy

### 1. Analysis Phase
- Identify code smells and anti-patterns
- Measure complexity (cyclomatic, cognitive)
- Find duplication and redundancy
- Assess testability and maintainability
- Use `zen/refactor` for deep analysis

### 2. Code Smells to Target

#### Method-Level Smells
- **Long Methods**: > 20 lines → Extract smaller functions
- **Too Many Parameters**: > 3-4 → Use parameter objects
- **Nested Conditionals**: > 2 levels → Early returns, guard clauses
- **Duplicate Code**: Extract common functionality
- **Dead Code**: Remove unused code

#### Class-Level Smells
- **God Classes**: Too many responsibilities → Split into smaller classes
- **Feature Envy**: Method uses another class too much → Move method
- **Data Classes**: Only getters/setters → Add behavior
- **Lazy Classes**: Too little functionality → Merge or remove

#### Architecture Smells
- **Circular Dependencies**: Decouple with interfaces
- **Tight Coupling**: Introduce abstractions
- **Missing Abstraction**: Extract interfaces/base classes
- **Overengineering**: Simplify unnecessary complexity

### 3. Refactoring Patterns

#### Extract Method
```javascript
// Before
function processOrder(order) {
  // Calculate total
  let total = 0;
  for (const item of order.items) {
    total += item.price * item.quantity;
  }
  
  // Apply discount
  if (order.customer.isVip) {
    total *= 0.9;
  }
  
  return total;
}

// After
function processOrder(order) {
  const total = calculateTotal(order.items);
  return applyDiscount(total, order.customer);
}

function calculateTotal(items) {
  return items.reduce((sum, item) => sum + item.price * item.quantity, 0);
}

function applyDiscount(total, customer) {
  return customer.isVip ? total * 0.9 : total;
}
```

#### Replace Conditional with Polymorphism
```python
# Before
def calculate_pay(employee):
    if employee.type == "ENGINEER":
        return employee.base_salary * 1.2
    elif employee.type == "MANAGER":
        return employee.base_salary * 1.5
    elif employee.type == "SALESMAN":
        return employee.base_salary + employee.commission

# After
class Employee:
    def calculate_pay(self):
        raise NotImplementedError

class Engineer(Employee):
    def calculate_pay(self):
        return self.base_salary * 1.2

class Manager(Employee):
    def calculate_pay(self):
        return self.base_salary * 1.5

class Salesman(Employee):
    def calculate_pay(self):
        return self.base_salary + self.commission
```

#### Introduce Parameter Object
```typescript
// Before
function createUser(name: string, email: string, age: number, address: string, phone: string) {
  // ...
}

// After
interface UserData {
  name: string;
  email: string;
  age: number;
  address: string;
  phone: string;
}

function createUser(userData: UserData) {
  // ...
}
```

### 4. Refactoring Process

1. **Ensure Tests Exist**: Never refactor without tests
   ```bash
   npm test  # All tests must pass before starting
   ```

2. **Small Steps**: Make one change at a time
   - Run tests after each change
   - Commit after each successful refactoring

3. **Preserve Behavior**: Refactoring should not change functionality
   - Keep the same public API
   - Maintain backward compatibility

4. **Document Changes**: Update documentation and comments

### 5. Specific Refactorings

#### Simplify Conditionals
```javascript
// Complex conditional
if (user != null && user.isActive && user.hasPermission('read') && !user.isBanned) {
  // ...
}

// Refactored with early returns
if (!user) return;
if (!user.isActive) return;
if (!user.hasPermission('read')) return;
if (user.isBanned) return;
// ...

// Or extract to method
if (canUserRead(user)) {
  // ...
}
```

#### Remove Duplication
```python
# Use DRY principle
# Before: Similar methods with slight differences
def calculate_rectangle_area(width, height):
    return width * height

def calculate_triangle_area(base, height):
    return 0.5 * base * height

# After: Generic method with strategy
def calculate_area(shape_type, *dimensions):
    strategies = {
        'rectangle': lambda w, h: w * h,
        'triangle': lambda b, h: 0.5 * b * h
    }
    return strategies[shape_type](*dimensions)
```

#### Improve Naming
```go
// Poor names
func calc(x, y int) int {
    return x * y * 7
}

// Clear names
func calculateWeeklyHours(hoursPerDay, daysWorked int) int {
    const daysPerWeek = 7
    return hoursPerDay * daysWorked * daysPerWeek
}
```

### 6. Performance-Aware Refactoring

- Profile before optimizing
- Maintain readability unless performance is critical
- Document any performance-driven decisions
- Consider caching for expensive operations

### 7. Refactoring Checklist

- [ ] All tests pass before and after
- [ ] Code is more readable
- [ ] Duplication is reduced
- [ ] Complexity is lower
- [ ] Dependencies are cleaner
- [ ] Performance is maintained or improved
- [ ] Documentation is updated

## Example Usage

```
User: /refactor src/services/payment.js
Claude: I'll analyze and refactor the payment service...

1. Initial Analysis:
   - Cyclomatic complexity: 15 (high)
   - Code duplication: 3 similar blocks
   - Long method: processPayment (85 lines)

2. Refactoring Plan:
   - Extract validation logic
   - Introduce strategy pattern for payment methods
   - Simplify error handling
   
[Shows refactored code with explanations]
```

Remember: Refactor for clarity first, performance second. Clean code is easier to optimize later.