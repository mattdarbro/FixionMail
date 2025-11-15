# FictionMail Product Roadmap & Feature Analysis

## Current Status: MVP Working ✓
- Bible enhancement from minimal input
- Standalone story generation (free: 1500w, premium: 4500w)
- Basic cameo system (implemented but needs UI)
- Rating system for preference learning
- Dev dashboard for testing

---

## Idea 1: Tier-based Bible Editing Restrictions

### Overview
Different tiers have different flexibility for modifying their story bible:

| Tier | Bible Edit Frequency | Scope of Changes |
|------|---------------------|------------------|
| **Free** | Once per month | Limited (genre-specific rules) |
| **Premium** | Once per day | Moderate (genre-specific rules) |
| **Creator** | Unlimited | Full control + story preview/editing |

### Implementation Complexity: **EASY to MEDIUM**

#### What's Needed:
1. **Database Schema Updates** (Easy)
   - Add `last_bible_edit_date` field to user records
   - Add `bible_edit_count` counter
   - Add `tier` field to user profile

2. **Edit Validation Logic** (Easy)
   ```python
   def can_edit_bible(user, requested_changes):
       # Check edit frequency based on tier
       if user.tier == "free":
           if days_since_last_edit(user) < 30:
               return False, "Free tier: 1 edit per month"
       elif user.tier == "premium":
           if days_since_last_edit(user) < 1:
               return False, "Premium tier: 1 edit per day"

       # Check scope of changes based on genre rules (Idea 2)
       return validate_changes_for_genre(user.bible, requested_changes)
   ```

3. **UI Updates** (Easy)
   - Show "Next edit available: X days" message
   - Disable edit button if locked
   - Show preview of what can/can't be changed

#### Estimated Implementation: **2-3 days**

---

## Idea 2: Genre-specific Consistency Rules

### Overview
Each genre has different rules about what elements remain consistent:

| Genre | Character Consistency | Setting Consistency | What Changes |
|-------|----------------------|---------------------|--------------|
| **Detective/Mystery** | HIGH - Same detective(s) | LOW - Different cases/locations | Investigation, mystery, clues |
| **Sci-Fi** | MEDIUM - Characters can evolve | HIGH - Same universe/world | Different situations in same world |
| **Sitcom** | HIGH - Same cast | HIGH - Same locations | Situations, conflicts, jokes |
| **Romance** | MEDIUM - Protagonist consistent | MEDIUM - Same "world" | Love interests, relationship arcs |
| **Adventure** | MEDIUM - Core team | LOW - Explore new places | Locations, quests, challenges |

### Implementation Complexity: **MEDIUM**

#### What's Needed:

1. **Genre Constraint Definitions** (Easy)
   ```python
   GENRE_RULES = {
       "mystery": {
           "protagonist": {"locked": True, "reason": "Detective identity is core"},
           "setting": {"locked": False, "can_change": ["location", "time_period"]},
           "supporting_chars": {"locked": False, "note": "Can add witnesses, suspects"},
           "core_elements": ["detective_trait", "investigation_style"]
       },
       "scifi": {
           "protagonist": {"locked": False, "can_evolve": True},
           "setting": {"locked": True, "reason": "Universe rules must be consistent"},
           "supporting_chars": {"locked": False},
           "core_elements": ["tech_level", "universe_rules", "species"]
       },
       "sitcom": {
           "protagonist": {"locked": True},
           "setting": {"locked": True, "reason": "Core locations stay same"},
           "supporting_chars": {"locked": True, "note": "Main cast consistent"},
           "core_elements": ["tone", "humor_style", "relationships"]
       }
   }
   ```

2. **Bible Edit Validator** (Medium)
   - Compare proposed changes against genre rules
   - Allow/block specific fields based on genre
   - Provide helpful messages: "In mystery stories, the detective stays the same but cases change"

3. **UI: Genre-aware Edit Forms** (Medium)
   - Show/hide editable fields based on genre
   - Add tooltips explaining why certain fields are locked
   - Highlight what CAN be changed for each genre

4. **Story Generation Updates** (Medium)
   - Modify prompts based on genre expectations
   - For mystery: "New investigation for [detective_name]"
   - For sci-fi: "New story in [universe_name] with [optional new character]"
   - For sitcom: "New situation involving [core_cast]"

#### Estimated Implementation: **4-5 days**

#### User Experience Examples:

**Mystery Genre (Premium tier, daily edit):**
```
✓ Can change: Investigation focus, new suspects, location
✗ Cannot change: Detective name/personality, investigation style
Next edit available: Tomorrow
```

**Sci-Fi Genre (Premium tier):**
```
✓ Can change: Characters (with evolution), new situations
✗ Cannot change: Universe tech level, core world rules
Locked: Your "Moon Colony" setting ensures consistency
```

**Sitcom Genre:**
```
✓ Can change: The situation/conflict for this episode
✗ Cannot change: Main characters, core locations
Note: Like a TV sitcom - same cast, different episodes!
```

---

## Idea 3: Universal Cameo Feature

### Overview
All tiers get cameo appearances (already partially implemented!). Users can:
- Define a cameo character (themselves, family member, friend)
- Character appears occasionally like Hitchcock in his films
- NOT the main character - just fun appearances

### Implementation Complexity: **EASY** ✓ (Mostly done!)

#### What's Already Built:
- ✅ Cameo data structure in bible
- ✅ Frequency settings (rarely, sometimes, often)
- ✅ Logic to include cameos in stories
- ✅ Prompts tell AI how to weave cameo in

#### What's Needed:

1. **UI for Cameo Setup** (Easy - 1 day)
   ```html
   <div class="cameo-section">
       <h3>Your Cameo Character (All Tiers)</h3>
       <input placeholder="Name (e.g., 'A mysterious stranger named Matt')">
       <textarea placeholder="Brief description (e.g., 'Always wears a purple hat and appears at key moments')"></textarea>
       <select>
           <option value="rarely">Rarely (15% of stories)</option>
           <option value="sometimes">Sometimes (30%)</option>
           <option value="often">Often (60%)</option>
       </select>
       <p class="hint">💡 Like Hitchcock in his films - a fun appearance, not the main character!</p>
   </div>
   ```

2. **Cameo Examples by Genre** (Backend already handles this)
   - Mystery: Cameo is a witness, informant, or red herring
   - Sci-Fi: Cameo is ship captain, alien trader, scientist
   - Sitcom: Cameo is quirky neighbor, delivery person, barista
   - Romance: Cameo is matchmaker, friend giving advice

#### Estimated Implementation: **1 day** (just needs UI)

---

## Idea 4: Special Genres & Modes

### Overview
Two special modes that break normal consistency rules:

**Mode A: Children's Stories**
- User specifies kids' names (e.g., "Gabbi and Olivia")
- Fairy tale style adventures
- Each story is self-contained
- Educational themes possible

**Mode B: "World Dips" Mode**
- Character consistency OFF
- Just explore the world with different characters
- Like anthology series set in same universe
- Good for sci-fi world-building

### Implementation Complexity: **MEDIUM to HARD**

#### 4A: Children's Story Genre

**Complexity: MEDIUM**

What's Needed:
1. **New Beat Template** (Easy)
   - Shorter word count (800-1200 words)
   - Simpler structure: Problem → Adventure → Lesson/Resolution
   - Age-appropriate language settings

2. **Character Input** (Easy)
   ```python
   children_bible = {
       "genre": "childrens",
       "characters": [
           {"name": "Gabbi", "age": 8, "traits": ["curious", "brave"]},
           {"name": "Olivia", "age": 6, "traits": ["creative", "kind"]}
       ],
       "themes": ["friendship", "problem-solving", "kindness"],
       "reading_level": "ages_6_10"
   }
   ```

3. **Prompt Modifications** (Medium)
   - Child-friendly language
   - Positive messages
   - No scary/inappropriate content
   - Clear moral or lesson

4. **Optional: Illustration Integration** (Hard - future)
   - Generate child-friendly images
   - Simple, colorful style

**Estimated Implementation: 3-4 days**

#### 4B: "World Dips" Mode (Anthology)

**Complexity: MEDIUM**

What's Needed:
1. **Mode Toggle** (Easy)
   ```python
   bible["consistency_mode"] = "anthology"  # vs "series"
   ```

2. **Modified Story Generation** (Medium)
   - Skip character consistency checks
   - Focus on world/setting consistency
   - Each story: new protagonist exploring same world
   - Prompt: "A new story set in [world], featuring [new character]"

3. **Bible Structure Changes** (Easy)
   ```python
   anthology_bible = {
       "genre": "scifi",
       "world": {  # This stays consistent
           "name": "Lunar Colonies",
           "tech_level": "near-future",
           "key_locations": ["Tranquility Base", "Mining Station 7"],
           "rules": ["Low gravity", "Enclosed habitats", "Earth visible"]
       },
       "character_template": {  # Used to generate new characters each time
           "role_pool": ["miner", "scientist", "tourist", "security"],
           "trait_pool": ["curious", "resourceful", "homesick", "ambitious"]
       },
       "consistency_mode": "anthology"
   }
   ```

4. **User Experience** (Easy)
   - Toggle: "Character Consistency: ON / OFF"
   - If OFF: Show "Anthology Mode - Each story features different characters in your world"

**Estimated Implementation: 3-4 days**

---

## Implementation Priority & Timeline

### Phase 1: Quick Wins (1-2 weeks)
1. ✅ **Cameo UI** (1 day) - Already mostly built, just needs frontend
2. **Tier Restrictions** (2-3 days) - Database + validation logic
3. **Children's Genre** (3-4 days) - New template + prompts

### Phase 2: Core Features (2-3 weeks)
4. **Genre-specific Rules** (4-5 days) - Most complex, most valuable
5. **Anthology Mode** (3-4 days) - Unlocks creative freedom

### Phase 3: Creator Tier (3-4 weeks - Post-MVP)
6. **Story Preview/Edit** (Hard) - Needs editor UI, save drafts, etc.
7. **Advanced Analytics** (Medium) - Show creator their readers' preferences
8. **Publishing Tools** (Hard) - Export, share, monetization

---

## Difficulty Scale Reference

| Rating | Effort | Example |
|--------|--------|---------|
| **EASY** | 1-2 days | UI updates, simple validation |
| **MEDIUM** | 3-5 days | New logic, prompt changes, schema updates |
| **HARD** | 1-2 weeks | Major new features, complex UI |
| **VERY HARD** | 2-4 weeks | Architecture changes, new systems |

---

## My Recommendations for MVP+

### Must Have (Critical for Product-Market Fit):
1. ✅ **Genre-specific Rules** (Idea 2) - This is your unique value prop
   - Users will LOVE that mystery works like Poirot
   - Sitcom works like Friends
   - This differentiates you from generic AI story generators

2. ✅ **Cameo Feature** (Idea 3) - Mostly done, easy win
   - Emotional connection = retention
   - "I'm in my own story!" = viral sharing

### Should Have (Great for Premium Conversion):
3. **Tier Restrictions** (Idea 1) - Clear value ladder
   - Free: Try it monthly
   - Premium: Daily stories = habit formation
   - Creator: Full control

### Nice to Have (Future Expansion):
4. **Children's Genre** (Idea 4A) - New market segment
   - Parents WILL pay for personalized stories for their kids
   - Consider separate product: "FictionMail Kids"

5. **Anthology Mode** (Idea 4B) - Power user feature
   - Great for creators who want to world-build
   - Maybe a Creator-tier exclusive?

---

## Technical Architecture Notes

### Database Schema Changes Needed:
```sql
-- User table additions
ALTER TABLE users ADD COLUMN tier VARCHAR(20) DEFAULT 'free';
ALTER TABLE users ADD COLUMN last_bible_edit_date TIMESTAMP;
ALTER TABLE users ADD COLUMN bible_edit_count INTEGER DEFAULT 0;

-- Bible table additions (if separate table)
ALTER TABLE story_bibles ADD COLUMN genre_rules JSONB;
ALTER TABLE story_bibles ADD COLUMN consistency_mode VARCHAR(20) DEFAULT 'series';
ALTER TABLE story_bibles ADD COLUMN cameo_character JSONB;
```

### New Backend Modules:
```
backend/
  storyteller/
    genre_rules.py          # NEW: Genre-specific constraints
    tier_validation.py      # NEW: Edit frequency checks
    children_prompts.py     # NEW: Child-friendly generation
    anthology_generation.py # NEW: Non-consistent character stories
```

---

## Questions to Consider:

1. **Monetization Strategy:**
   - Monthly subscription vs credits?
   - Free tier: 1 story/month or 1 story/week?
   - Premium tier: 1 story/day = $9.99/mo?
   - Creator tier: Unlimited + tools = $29.99/mo?

2. **Story Delivery:**
   - Email (as planned)?
   - In-app reading?
   - Scheduled send time (morning coffee vs evening wind-down)?

3. **Social Features:**
   - Can users share stories publicly?
   - "Reader mode" for following other creators?
   - Comments/reactions?

4. **Content Safety:**
   - How to handle inappropriate prompts?
   - Age verification for children's mode?
   - Content filters by tier?

---

## Summary: What's Actually Hard?

### Easy Stuff (Already 80% Done):
- ✅ Basic story generation
- ✅ Bible enhancement
- ✅ Tier-based word counts
- ✅ Cameo system (backend)

### Medium Complexity (Well-defined, doable):
- Genre-specific rules (clear logic, just needs implementation)
- Tier restrictions (standard SaaS feature)
- Children's genre (new prompts + templates)
- Anthology mode (existing code + small tweaks)

### Hard Stuff (Post-MVP):
- Creator preview/editing (needs complex UI)
- Real email delivery system (infrastructure)
- Payment/subscription system (use Stripe, but still work)
- Mobile apps (if desired)

### Your Best Next Step:
**Implement Genre-Specific Rules (Idea 2) first.**

Why?
- It's the unique selling point
- Medium difficulty (not too hard)
- Makes free tier valuable enough to hook users
- Makes premium tier obviously worth paying for
- Sets foundation for everything else

Want me to start building Idea 2 (genre rules)?
