class StoryGenerator {
  constructor() {
    this.apiKey = process.env.OPENAI_API_KEY || process.env.ANTHROPIC_API_KEY;
    this.apiType = process.env.OPENAI_API_KEY ? 'openai' : 'anthropic';
  }

  async generateNarrative(command, args, result, character) {
    if (!this.apiKey) {
      // Fallback to predefined narratives if no API key
      return this.getFallbackNarrative(command, args, result, character);
    }

    const prompt = this.buildNarrativePrompt(command, args, result, character);
    
    try {
      if (this.apiType === 'openai') {
        return await this.generateWithOpenAI(prompt);
      } else {
        return await this.generateWithAnthropic(prompt);
      }
    } catch (error) {
      console.error('Story generation error:', error);
      return this.getFallbackNarrative(command, args, result, character);
    }
  }

  buildNarrativePrompt(command, args, result, character) {
    return `You are a narrator for a Black Sails-inspired pirate adventure game set in 1715 Nassau.

Character: ${character.name} (${character.faction})
Location: ${character.location}
Command: ${command} ${args.join(' ')}
Result: ${JSON.stringify(result)}

Generate a brief, atmospheric narrative response (2-3 sentences) that:
1. Describes the action in vivid, period-appropriate language
2. Includes sensory details (sights, sounds, smells)
3. Maintains the gritty, realistic tone of Black Sails
4. Avoids modern language or anachronisms

Respond only with the narrative text, no additional formatting.`;
  }

  async generateWithOpenAI(prompt) {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`
      },
      body: JSON.stringify({
        model: 'gpt-4',
        messages: [
          {
            role: 'system',
            content: 'You are a narrative generator for a pirate adventure game inspired by Black Sails.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.8,
        max_tokens: 150
      })
    });

    const data = await response.json();
    return data.choices[0].message.content;
  }

  async generateWithAnthropic(prompt) {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': this.apiKey,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-3-sonnet-20240229',
        messages: [
          {
            role: 'user',
            content: prompt
          }
        ],
        max_tokens: 150,
        temperature: 0.8
      })
    });

    const data = await response.json();
    return data.content[0].text;
  }

  async generateNPCDialogue(npc, character) {
    if (!this.apiKey) {
      return this.getFallbackDialogue(npc, character);
    }

    const prompt = `You are ${npc.name}, a ${npc.npc_type} in 1715 Nassau. 
Your faction: ${npc.faction || 'independent'}
Speaking to: ${character.name} (${character.faction})
Character reputation with your faction: ${await this.getReputation(character, npc.faction)}

Generate a single line of dialogue that:
1. Reflects your character's personality and role
2. Considers the character's faction and reputation
3. Uses period-appropriate language
4. Might hint at quests or information
5. Stays true to Black Sails' tone

Respond only with the dialogue, no quotes or attribution.`;

    try {
      if (this.apiType === 'openai') {
        return await this.generateWithOpenAI(prompt);
      } else {
        return await this.generateWithAnthropic(prompt);
      }
    } catch (error) {
      console.error('Dialogue generation error:', error);
      return this.getFallbackDialogue(npc, character);
    }
  }

  async getReputation(character, faction) {
    // This would query the database in a real implementation
    return 0;
  }

  getFallbackNarrative(command, args, result, character) {
    const narratives = {
      move: [
        "Your boots echo on the cobblestones as you make your way through the crowded streets.",
        "The Caribbean sun beats down as you navigate through the bustling port.",
        "You push through the crowd of pirates and merchants, the smell of rum and gunpowder thick in the air."
      ],
      sail: [
        "The wind fills your sails as your crew prepares for the journey ahead.",
        "Your ship cuts through the azure waters, spray misting across the deck.",
        "The crew springs into action, unfurling sails and weighing anchor."
      ],
      talk: [
        "You approach cautiously, hand resting on your pistol.",
        "The conversation draws curious glances from nearby pirates.",
        "Words are carefully chosen in this den of thieves and cutthroats."
      ],
      attack: [
        "Steel rings as you draw your blade, the crowd quickly backing away.",
        "The tension breaks like a thunderclap as violence erupts.",
        "Your hand moves to your weapon as killing intent fills the air."
      ],
      look: [
        "You survey your surroundings with a practiced eye, noting every detail.",
        "Your gaze sweeps across the scene, cataloging threats and opportunities.",
        "You take in the sights and sounds of this lawless place."
      ]
    };

    const options = narratives[command] || narratives.look;
    return options[Math.floor(Math.random() * options.length)];
  }

  getFallbackDialogue(npc, character) {
    const dialogues = {
      'Eleanor Guthrie': [
        "The Guthrie name still carries weight in Nassau, despite what some might think.",
        "If you're looking for work, prove yourself useful first.",
        "Nassau runs on trade, not ideals. Remember that."
      ],
      'Captain Hornigold': [
        "The fort needs men who can follow orders and handle themselves in a fight.",
        "Nassau was built by pirates, for pirates. We'll not see it fall to the British.",
        "A good sailor is worth his weight in gold these days."
      ],
      'Max': [
        "Information has a price, same as everything else in Nassau.",
        "I hear many things in my establishment. What's it worth to you?",
        "Trust is a luxury few can afford here."
      ],
      'default': [
        "Nassau's a dangerous place for those who don't know its ways.",
        "Keep your wits about you in these streets.",
        "Every man has a price here. What's yours?"
      ]
    };

    const options = dialogues[npc.name] || dialogues.default;
    return options[Math.floor(Math.random() * options.length)];
  }

  async generateQuestDescription(questTemplate, worldState) {
    // Generate dynamic quest descriptions based on world state
    const baseDescription = questTemplate.description;
    
    // Add world-specific details
    if (worldState.events && worldState.events.length > 0) {
      const latestEvent = worldState.events[worldState.events.length - 1];
      if (latestEvent.type === 'storm') {
        return baseDescription + " The recent storm has made sea travel more dangerous.";
      }
    }

    return baseDescription;
  }

  async generateEventNarrative(event, affectedCharacters) {
    // Generate narrative for world events
    const eventNarratives = {
      storm: "Dark clouds gather on the horizon as the barometer drops. A storm is brewing in the Caribbean.",
      navy_patrol: "Word spreads through the taverns - British warships have been spotted in nearby waters.",
      treasure_rumor: "Whispers in the shadows speak of Spanish gold, hidden away on a forgotten island.",
      market_crash: "Panic grips the merchants as prices plummet. Someone has flooded the market.",
      pirate_raid: "Black sails appear on the horizon. Another crew has struck at a merchant convoy."
    };

    return eventNarratives[event.type] || "Something stirs in Nassau...";
  }
}

module.exports = new StoryGenerator();