"""NPC definitions and dialogue"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import random


@dataclass
class NPC:
    """Non-player character"""
    name: str
    description: str
    dialogue: List[str]
    merchant: bool = False
    quest_giver: bool = False
    combat_level: int = 1  # 1-5 difficulty
    
    def get_random_dialogue(self) -> str:
        """Get a random dialogue line"""
        return random.choice(self.dialogue)


# NPC Database
NPCS = {
    "flint's parrot": NPC(
        name="Flint's Parrot",
        description="A mangy parrot that somehow knows everyone's secrets. And curses. So many curses.",
        dialogue=[
            "SQUAWK! 'Pieces of eight! Also, the governor hides his gold in his left boot!' SQUAWK!",
            "SQUAWK! 'Dead men tell no tales! But parrots do! Want to know who cheats at dice?' SQUAWK!",
            "SQUAWK! 'Polly wants a cracker! Also wants to tell you about the secret tunnel!' SQUAWK!",
            "*The parrot eyes your coin purse* SQUAWK! 'Nice gold! Be a shame if someone... STOLE IT!' SQUAWK!",
            "SQUAWK! 'I taught Flint everything he knows! Mostly swear words!' SQUAWK!"
        ],
        quest_giver=True
    ),
    
    "one-legged pete": NPC(
        name="One-Legged Pete",
        description="Pete has the worst luck in Nassau. He's currently losing a game he's not even playing.",
        dialogue=[
            "'I once had two legs, then I bet one in a game of dice. Don't ask about the eye patch.'",
            "'Just lost another bet. This time to a seagull. Don't ask how.'",
            "'Want to hear about my lucky day? Neither do I, never had one.'",
            "'I'm not saying I'm unlucky, but I once drowned in a desert.'",
            "'They call me One-Legged Pete. Used to be No-Legged Pete, so things are looking up!'"
        ],
        combat_level=1
    ),
    
    "dramatic dave": NPC(
        name="Dramatic Dave",
        description="Dave gestures wildly as he speaks. 'Dramatic Dave examines you examining him!'",
        dialogue=[
            "'Dramatic Dave speaks to you with great intensity about absolutely nothing!'",
            "'BEHOLD!' *gestures at nothing* 'The very AIR ITSELF trembles at Dramatic Dave's presence!'",
            "'Dramatic Dave's heart POUNDS with the rhythm of DESTINY! Also indigestion!'",
            "'You dare approach Dramatic Dave?! How... DRAMATIC!'",
            "*whispers dramatically* 'dramatic dave sometimes forgets to stop being dramatic'"
        ],
        combat_level=2
    ),
    
    "the philosophical pirate": NPC(
        name="The Philosophical Pirate",
        description="'To steal or not to steal,' he muses, 'that is never the question. The question is: how much?'",
        dialogue=[
            "'Is a ship still a ship if you replace every plank? Anyway, want to buy some planks?'",
            "'I think, therefore I pirate. Descartes said that. Or was it me? Hard to tell.'",
            "'If a tree falls in the forest and no one's around, I probably stole it.'",
            "'The unexamined life is not worth living. The examined life? Also questionable.'",
            "'What is truth? What is beauty? What is the combination to the governor's safe?'"
        ],
        merchant=True,
        combat_level=3
    ),
    
    "nervous ned": NPC(
        name="Nervous Ned",
        description="Ned jumps at your gaze. His pockets jingle with hastily grabbed coins.",
        dialogue=[
            "'I didn't take it! Whatever it is! Oh, you're just talking? ...I still didn't take it.'",
            "*jumps* 'Oh! You scared me! I mean, I wasn't doing anything suspicious!'",
            "'Why does everyone always think I'm nervous? *twitch* I'm perfectly calm!'",
            "'That noise? What noise? I didn't hear any noise! WHAT WAS THAT?!'",
            "'I'm not running FROM something, I'm running TO... somewhere else!'"
        ],
        combat_level=1
    ),
    
    "mad mary": NPC(
        name="Mad Mary",
        description="Her 'potions' are definitely just rum with food coloring. The prices, however, are very real.",
        dialogue=[
            "'My potions cure what ails ye! Side effects include: everything ailing ye twice as bad.'",
            "'This one makes you invisible! To yourself. Everyone else can still see you.'",
            "'Love potion? Sure! Makes you fall in love with spending money on more potions!'",
            "'This blue one grants wisdom! You'll wisely realize you shouldn't have drunk it!'",
            "'Special today: Buy two useless potions, get a third useless potion free!'"
        ],
        merchant=True
    ),
    
    "the overly honest thief": NPC(
        name="The Overly Honest Thief",
        description="'I'm going to pick your pocket now,' he announces helpfully.",
        dialogue=[
            "'Hello! I'm planning to rob you later. Around 3 o'clock work for you?'",
            "'I'm about to steal your gold. Just wanted to be transparent about it.'",
            "'Fair warning: I'm a thief. Terrible at it though, I keep telling people.'",
            "'I've stolen from everyone here! Well, tried to. The announcing part ruins it.'",
            "'Your pocket has a hole in it. I know because I was just in there.'"
        ],
        combat_level=2
    ),
    
    "eleanor guthrie": NPC(
        name="Eleanor Guthrie",
        description="The real power in Nassau. Her ledger is mightier than any sword.",
        dialogue=[
            "'If you're not here to trade, you're here to waste my time. Which is it?'",
            "'The only law in Nassau is profit. Break that law and you'll wish for the gallows.'",
            "'I've seen tougher pirates than you crying into their rum. What makes you special?'",
            "'Every man has a price. Yours looks particularly cheap.'",
            "'Nassau runs on three things: gold, rum, and my patience. You're testing the third.'"
        ],
        merchant=True,
        quest_giver=True,
        combat_level=5
    ),
    
    "gambling denis": NPC(
        name="Gambling Denis",
        description="Denis runs the 'honest' dice games. The dice are loaded, but honestly loaded.",
        dialogue=[
            "'Step right up! Fair dice, fair odds, fairly certain you'll lose!'",
            "'The house always wins! I am the house. The house needs new shoes.'",
            "'Double or nothing! Or as I call it, nothing or nothing!'",
            "'These dice aren't loaded! They're just... gravitationally enhanced.'",
            "'I'll give you 3-to-1 odds. Three of my wins to one of yours!'"
        ],
        merchant=True
    ),
    
    "cheating charlie": NPC(
        name="Cheating Charlie",
        description="Charlie doesn't even try to hide his cheating. He's holding extra cards right now.",
        dialogue=[
            "'Five aces is a legitimate hand! I read it in a book I wrote.'",
            "'That card fell out of my sleeve by accident. The other six were intentional.'",
            "'I'm not cheating, I'm just playing with advanced rules you wouldn't understand.'",
            "'Want to play cards? I'll deal. From the bottom. While you watch.'",
            "'I never cheat! I just creatively interpret the rules in my favor.'"
        ]
    ),
    
    "judgmental seagull": NPC(
        name="Judgmental Seagull",
        description="*The seagull stares at you with disappointment*",
        dialogue=[
            "*SQUAWK* (It sounds disapproving)",
            "*The seagull shakes its head at your life choices*",
            "*It pecks at your boots judgmentally*",
            "*The seagull looks at your weapon and laughs. A seagull. Laughed at you.*",
            "*It flies away, but not before giving you one last disappointed look*"
        ]
    ),
    
    "british guard": NPC(
        name="British Guard",
        description="Sweating profusely in his uniform, he's clearly questioning his life choices.",
        dialogue=[
            "'Move along, citizen. Nothing to see here except my slow death by heatstroke.'",
            "'The Queen's justice will prevail! Once I figure out which queen we're serving now.'",
            "'You there! Stop! Or don't. It's too hot to chase you.'",
            "'I joined the Navy to see the world. All I've seen is sweat and pirates.'",
            "'Papers please. Actually, forget it. Papers would just get soggy from sweat.'"
        ],
        combat_level=3
    ),
    
    "lost tourist": NPC(
        name="Lost Tourist",
        description="How did they even get here? They're holding a map upside down.",
        dialogue=[
            "'Is this the Caribbean? The travel agent said it would be more... resort-y.'",
            "'Excuse me, where's the nearest Starbucks? What do you mean what's a Starbucks?'",
            "'I'm looking for the tourist information center. This can't be it, right?'",
            "'My guidebook said Nassau was a paradise! It didn't mention the stabbing!'",
            "'Do you know the WiFi password? No? What kind of establishment is this?'"
        ]
    ),
    
    "salty sam the shipwright": NPC(
        name="Salty Sam the Shipwright",
        description="Sam's been building ships for decades. Most of them even float.",
        dialogue=[
            "'I can fix your ship! Might even be seaworthy when I'm done!'",
            "'That'll buff right out. The hole, the mast, the fact it's underwater...'",
            "'I've built hundreds of ships! Sunk most of them too, but that's beside the point.'",
            "'She's a beautiful vessel! If you squint. In the dark. While drunk.'",
            "'Wood? Nails? Craftsmanship? Bah! Ships float on hope and prayer!'"
        ],
        merchant=True
    )
}