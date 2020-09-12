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
    def __init__(self, sp_weight, dot_duration, hit_interval, cast_time, cooldown):
        self.spell_damage = sp_weight*intellect*(1+haste_percent)
        self.dot_duration = dot_duration
        self.dot_hit_interval = hit_interval / (1+haste_percent)
        self.cast_time = cast_time/(1+haste_percent)
        # Check to see if cooldowns change with haste
        self.cooldown = cooldown


class Channeled:
    """Creates stats for channeled spells"""
    def __init__(self, sp_weight, dot_duration, hit_interval):
        self.spell_damage = sp_weight*intellect
        self.dot_duration = dot_duration
        self.hit_interval = hit_interval / (1+haste_percent)


class Timeline:
    """A timeline class which will keep track of the possible events that can occur"""
    now = 0
    schism_hit = float('inf')
    schism_off_cd = 0


def schism_attack(fmob_hp, ftimeline):
    """Modifies timeline and mob hitpoints resulting from a schism attack."""
    fmob_hp -= schism.spell_damage
    ftimeline.schism_hit = float('inf')
    ftimeline.schism_off_cd = ftimeline.now + schism.cooldown
    return fmob_hp, ftimeline


def next_time_stop():
    """Determines next value for timeline.now"""
    if min([timeline.schism_hit]) < float('inf'):
        return min([timeline.schism_hit])
    else:
        return min([timeline.schism_off_cd])


def next_spell(ftimeline):
    """After a spell is cast or a cooldown is run into, this determines which spell should be cast next."""
    if ftimeline.now >= ftimeline.schism_off_cd:
        ftimeline.schism_hit = ftimeline.now + schism.cast_time
    return ftimeline


def execute_time_stop(fmob_hp, ftimeline):
    if ftimeline.now == ftimeline.schism_hit:
        fmob_hp, ftimeline = schism_attack(fmob_hp, ftimeline)
    return fmob_hp, ftimeline


def kill_one(ftimeline):
    mob_hp = int(random.randrange(mob_min_hp, mob_max_hp+1))
    while mob_hp > 0:
        ftimeline.now = next_time_stop()
        mob_hp, ftimeline = execute_time_stop(mob_hp, ftimeline)


intellect = 7189
crit_rating = 1273
haste_rating = 473
mastery_rating = 716
versatility_rating = 331

crit_chance = crit_rating*0.1768/1273
haste_percent = haste_rating*0.0696/473
mastery_percent = mastery_rating*0.1343/716
versatility_percent = versatility_rating*0.0389/331

schism = Spells(1.29, 7.77, 1.5, 12)


timeline = Timeline
insanity = 0

mob_min_hp = 40000
mob_max_hp = 50000

print(f'Haste %: {haste_percent}')
print(f'Crit chance: {crit_chance}')
print(f'Mastery %: {mastery_percent}')
print(f'Versatility %: {versatility_percent}')

print(next_time_stop())
