import random
import math


class Spells:
    """Creates stats for direct damage spells"""
    def __init__(self, sp_weight, sp_bias, cast_time, cooldown):
        self.spell_damage = sp_weight*intellect + sp_bias
        self.cast_time = cast_time/(1+haste_percent)
        self.cooldown = cooldown


class Dots:
    """Creates stats for damage-over-time spells"""
    def __init__(self, sp_weight, sp_bias, dot_duration, hit_interval, cast_time, cooldown):
        self.dot_hit_damage = (sp_weight*intellect + sp_bias)/(dot_duration/hit_interval)
        self.dot_hit_interval = hit_interval / (1+haste_percent)
        self.dot_duration = dot_duration
        self.cast_time = cast_time/(1+haste_percent)
        self.cooldown = cooldown
        self.last_hit_coeff = 0


class Channeled:
    """Creates stats for channeled spells"""
    def __init__(self, sp_weight, dot_duration, hit_interval):
        self.spell_damage = sp_weight*intellect
        self.dot_duration = dot_duration
        self.hit_interval = hit_interval / (1+haste_percent)


class Timeline:
    """A timeline class which will keep track of the possible events that can occur"""
    now = 0
    gcd_end = float('inf')
    schism_hit = float('inf')
    schism_off_cd = 0
    # Schism Debuff increases damage taken by 40% for 9 seconds.
    schism_debuff_end = 0
    pain_dd_hit = float('inf')
    pain_dot_hit = float('inf')
    pain_dot_end = 0
    pain_dot_last_hit = float('inf')
    smite_hit = float('inf')


def schism_attack(fmob_hp, ftimeline):
    """Adjusts timeline and hitpoints after a Schism attack."""
    crit_boolean = random.choices([True, False], weights=[crit_chance, 1-crit_chance])[0]
    if ftimeline.now <= ftimeline.schism_debuff_end:
        schism_buff = True
    else:
        schism_buff = False
    damage = int(schism.spell_damage*(1+versatility_percent)*(1+schism_buff*0.4))
    if crit_boolean:
        print(f'Schism crit for {damage*2} at {ftimeline.now:.2f}s.')
        fmob_hp -= damage*2
        print(f'Mob HP: {fmob_hp}.')
    else:
        print(f'Schism hit for {damage} at {ftimeline.now:.2f}s.')
        fmob_hp -= damage
        print(f'Mob HP: {fmob_hp}.')
    ftimeline.schism_hit = float('inf')
    ftimeline.schism_off_cd = ftimeline.now + schism.cooldown
    ftimeline.schism_debuff_end = ftimeline.now + 9
    ftimeline = next_spell(ftimeline)
    return fmob_hp, ftimeline


def pain_dd_attack(fmob_hp, ftimeline):
    """Adjusts timeline and hitpoints after the direct damage portion of SW: Pain."""
    crit_boolean = random.choices([True, False], weights=[crit_chance, 1-crit_chance])[0]
    if ftimeline.now <= ftimeline.schism_debuff_end:
        schism_buff = True
    else:
        schism_buff = False
    damage = int(pain_dd.spell_damage*(1+versatility_percent)*(1+schism_buff*0.4))
    if crit_boolean:
        print(f'SW: Pain DD crit for {damage*2} at {ftimeline.now:.2f}s.')
        fmob_hp -= damage*2
        print(f'Mob HP: {fmob_hp}.')
    else:
        print(f'SW: Pain DD hit for {damage} at {ftimeline.now:.2f}s.')
        fmob_hp -= damage
        print(f'Mob HP: {fmob_hp}.')
    ftimeline.pain_dd_hit = float('inf')
    ftimeline.pain_dot_end = ftimeline.now + pain_dot.dot_duration
    ftimeline.pain_dot_hit = ftimeline.now + pain_dot.dot_hit_interval
    ftimeline.gcd_end = ftimeline.now + global_cd.cast_time
    return fmob_hp, ftimeline


def pain_dot_attack(fmob_hp, ftimeline, fpain_dot):
    """Adjusts timeline and hitpoints after a SW: Pain DoT hit."""
    crit_boolean = random.choices([True, False], weights=[crit_chance, 1-crit_chance])[0]
    if ftimeline.now <= ftimeline.schism_debuff_end:
        schism_buff = True
    else:
        schism_buff = False
    damage = int(pain_dd.spell_damage*(1+versatility_percent)*(1+schism_buff*0.4))
    if crit_boolean:
        print(f'SW: Pain DoT crit for {damage*2} at {ftimeline.now:.2f}s.')
        fmob_hp -= damage*2
        print(f'Mob HP: {fmob_hp}.')
    else:
        print(f'SW: Pain DoT hit for {damage} at {ftimeline.now:.2f}s.')
        fmob_hp -= damage
        print(f'Mob HP: {fmob_hp}.')
    # This sets when the next dot hit will occur.
    if ftimeline.now + fpain_dot.dot_hit_interval <= ftimeline.pain_dot_end:
        ftimeline.pain_dot_hit = ftimeline.now + fpain_dot.dot_hit_interval
    else:
        fpain_dot.last_hit_coeff = (ftimeline.pain_dot_end - ftimeline.now)/fpain_dot.dot_hit_interval
        ftimeline.pain_dot_last_hit = ftimeline.pain_dot_end
        ftimeline.pain_dot_hit = float('inf')
    return fmob_hp, ftimeline, fpain_dot


def pain_last_dot_attack(fmob_hp, ftimeline, fpain_dot):
    """Adjusts timeline and hitpoints after a SW: Pain DoT hit."""
    crit_boolean = random.choices([True, False], weights=[crit_chance, 1-crit_chance])[0]
    if ftimeline.now <= ftimeline.schism_debuff_end:
        schism_buff = True
    else:
        schism_buff = False
    damage = int(pain_dd.spell_damage*(1+versatility_percent)*(1+schism_buff*0.4)*fpain_dot.last_hit_coeff)
    if crit_boolean:
        print(f'SW: Pain DoT crit for {damage*2} at {ftimeline.now:.2f}s.')
        fmob_hp -= damage*2
        print(f'Mob HP: {fmob_hp}.')
    else:
        print(f'SW: Pain DoT hit for {damage} at {ftimeline.now:.2f}s.')
        fmob_hp -= damage
        print(f'Mob HP: {fmob_hp}.')
    ftimeline.pain_dot_end = 0
    ftimeline.pain_dot_last_hit = float('inf')
    return fmob_hp, ftimeline


def smite_attack(fmob_hp, ftimeline):
    """Adjusts timeline and hitpoints after a Schism attack."""
    crit_boolean = random.choices([True, False], weights=[crit_chance, 1-crit_chance])[0]
    if ftimeline.now <= ftimeline.schism_debuff_end:
        schism_buff = True
    else:
        schism_buff = False
    damage = int(smite.spell_damage*(1+versatility_percent)*(1+schism_buff*0.4))
    if crit_boolean:
        print(f'Smite crit for {damage*2} at {ftimeline.now:.2f}s.')
        fmob_hp -= damage*2
        print(f'Mob HP: {fmob_hp}.')
    else:
        print(f'Smite hit for {damage} at {ftimeline.now:.2f}s.')
        fmob_hp -= damage
        print(f'Mob HP: {fmob_hp}.')
    ftimeline.smite_hit = float('inf')
    ftimeline = next_spell(ftimeline)
    return fmob_hp, ftimeline


def next_time_stop():
    """Determines next value for timeline.now"""
    # Values that default to zero can't be included in the list or they'll be the min value every time.
    events_list = [timeline.schism_hit, timeline.pain_dd_hit, timeline.gcd_end, timeline.smite_hit,
                   timeline.pain_dot_hit, timeline.pain_dot_last_hit]
    # if timeline.timeline.pain_dot_end > 0:
    #     events_list.append(timeline.pain_dot_end)
    return min(events_list)


def next_spell(ftimeline):
    """After certain spells are cast or the GCD expires, this determines which spell should be cast next."""
    if ftimeline.now >= ftimeline.schism_off_cd:
        ftimeline.schism_hit = ftimeline.now + schism.cast_time
    elif ftimeline.now >= ftimeline.pain_dot_end:
        ftimeline.pain_dd_hit = ftimeline.now
    else:
        ftimeline.smite_hit = ftimeline.now + smite.cast_time
    return ftimeline


def execute_time_stop(fmob_hp, ftimeline, fpain_dot):
    """Given a timestop, this determines which action should be taken."""
    if ftimeline.now == ftimeline.pain_dot_hit:
        fmob_hp, ftimeline, fpain_dot = pain_dot_attack(fmob_hp, ftimeline, fpain_dot)
    elif ftimeline.now == ftimeline.pain_dot_last_hit:
        fmob_hp, ftimeline = pain_last_dot_attack(fmob_hp, ftimeline, fpain_dot)
    elif ftimeline.now == ftimeline.schism_hit:
        fmob_hp, ftimeline = schism_attack(fmob_hp, ftimeline)
    elif ftimeline.now == ftimeline.pain_dd_hit:
        fmob_hp, ftimeline = pain_dd_attack(fmob_hp, ftimeline)
    elif ftimeline.now == ftimeline.gcd_end:
        ftimeline.gcd_end = float('inf')
        ftimeline = next_spell(ftimeline)
    elif ftimeline.now == ftimeline.smite_hit:
        fmob_hp, ftimeline = smite_attack(fmob_hp, ftimeline)
    # I don't think I need this, but I'll keep it for a little bit.
    # else:
    #     ftimeline = next_spell(ftimeline)
    return fmob_hp, ftimeline, fpain_dot


def kill_one(ftimeline, fmob_num, fpain_dot):
    mob_hp = int(random.randrange(mob_min_hp, mob_max_hp+1))
    print(f'Mob {fmob_num} HP: {mob_hp}.')
    ftimeline = next_spell(ftimeline)
    while mob_hp > 0:
        ftimeline.now = next_time_stop()
        mob_hp, ftimeline, fpain_dot = execute_time_stop(mob_hp, ftimeline, fpain_dot)
    print(f'Mob {fmob_num} died at {ftimeline.now:.2f}.')
    return ftimeline, fmob_num, fpain_dot


intellect = 7189
crit_rating = 1273
haste_rating = 473
mastery_rating = 716
versatility_rating = 331

crit_chance = crit_rating*0.1768/1273
haste_percent = haste_rating*0.0696/473
mastery_percent = mastery_rating*0.1343/716
versatility_percent = versatility_rating*0.0389/331

global_cd = Spells(0, 0, 1.5, 0)
schism = Spells(1.29, 7.77, 1.5, 24)
pain_dd = Spells(0.165, 0.858, 0, 0)
smite = Spells(0.57, 3.26, 1.5, 0)
pain_dot = Dots(0.992, 1.31, 16, 2, 0, 0)

timeline = Timeline
insanity = 0
mob_number = 1

mob_min_hp = 40000
mob_max_hp = 172000

print(f'Haste: {haste_percent:.2%}')
print(f'Crit: {crit_chance:.2%}')
print(f'Mastery: {mastery_percent:.2%}')
print(f'Versatility: {versatility_percent:.2%}\n')

timeline, mob_number, pain_dot = kill_one(timeline, mob_number, pain_dot)
