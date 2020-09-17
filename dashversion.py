import random
from flask import Blueprint
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State


semdoms_bp = Blueprint('semdoms_bp', __name__,
                       static_folder='static',
                       template_folder='templates',
                       static_url_path='/discsim/static')


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
    def __init__(self, sp_weight, sp_bias, hits, channel_duration, cooldown):
        self.hit_damage = (sp_weight*intellect + sp_bias)/hits
        self.hit_interval = (channel_duration / (1+haste_percent))/hits
        self.cooldown = cooldown
        self.hit_count = 1


class Star:
    """Creates stats for Divine Star"""
    def __init__(self, sp_weight, sp_bias, cooldown):
        self.hit_damage = (sp_weight*intellect + sp_bias)/2
        self.cooldown = cooldown
        self.hit_count = 1


class Log:
    """This is for logging data that will be passed to the timeline graph."""
    def __init__(self):
        self.time_list = []
        self.spell_list = []
        self.damage_list = []
        self.color_list = []

    def update(self, time, spell, damage, color):
        self.time_list.append(time)
        self.spell_list.append(spell)
        self.damage_list.append(damage)
        self.color_list.append(color)


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
    penance_hit = float('inf')
    penance_off_cd = 0
    solace_hit = float('inf')
    solace_off_cd = 0
    divine_star_hit = float('inf')
    divine_star_off_cd = 0


def schism_attack(fmob_hp, ftimeline, flog):
    """Adjusts timeline and hitpoints after a Schism attack."""
    crit_boolean = random.choices([True, False], weights=[crit_chance, 1-crit_chance])[0]
    if ftimeline.now <= ftimeline.schism_debuff_end:
        schism_buff = True
    else:
        schism_buff = False
    damage = int(schism.spell_damage*(1+versatility_percent)*(1+schism_buff*0.4))
    if crit_boolean:
        print(f'Schism crit for {damage*2} at {ftimeline.now:.2f}s.')
        flog.update(ftimeline.now, 'Schism', damage*2, '#26272D')
        fmob_hp -= damage*2
        print(f'Mob HP: {fmob_hp}.')
    else:
        print(f'Schism hit for {damage} at {ftimeline.now:.2f}s.')
        flog.update(ftimeline.now, 'Schism', damage, '#26272D')
        fmob_hp -= damage
        print(f'Mob HP: {fmob_hp}.')
    ftimeline.schism_hit = float('inf')
    ftimeline.schism_off_cd = ftimeline.now + schism.cooldown
    ftimeline.schism_debuff_end = ftimeline.now + 9
    ftimeline = next_spell(ftimeline)
    return fmob_hp, ftimeline, flog


def pain_dd_attack(fmob_hp, ftimeline, flog):
    """Adjusts timeline and hitpoints after the direct damage portion of SW: Pain."""
    crit_boolean = random.choices([True, False], weights=[crit_chance, 1-crit_chance])[0]
    if ftimeline.now <= ftimeline.schism_debuff_end:
        schism_buff = True
    else:
        schism_buff = False
    damage = int(pain_dd.spell_damage*(1+versatility_percent)*(1+schism_buff*0.4))
    if crit_boolean:
        print(f'SW: Pain DD crit for {damage*2} at {ftimeline.now:.2f}s.')
        flog.update(ftimeline.now, 'SW: Pain Initial Hit', damage*2, '#C52D2D')
        fmob_hp -= damage*2
        print(f'Mob HP: {fmob_hp}.')
    else:
        print(f'SW: Pain DD hit for {damage} at {ftimeline.now:.2f}s.')
        flog.update(ftimeline.now, 'SW: Pain Initial Hit', damage, '#C52D2D')
        fmob_hp -= damage
        print(f'Mob HP: {fmob_hp}.')
    ftimeline.pain_dd_hit = float('inf')
    ftimeline.pain_dot_end = ftimeline.now + pain_dot.dot_duration
    ftimeline.pain_dot_hit = ftimeline.now + pain_dot.dot_hit_interval
    ftimeline.gcd_end = ftimeline.now + global_cd.cast_time
    return fmob_hp, ftimeline, flog


def pain_dot_attack(fmob_hp, ftimeline, fpain_dot, flog):
    """Adjusts timeline and hitpoints after a SW: Pain DoT hit."""
    crit_boolean = random.choices([True, False], weights=[crit_chance, 1-crit_chance])[0]
    if ftimeline.now <= ftimeline.schism_debuff_end:
        schism_buff = True
    else:
        schism_buff = False
    damage = int(pain_dd.spell_damage*(1+versatility_percent)*(1+schism_buff*0.4))
    if crit_boolean:
        print(f'SW: Pain DoT crit for {damage*2} at {ftimeline.now:.2f}s.')
        flog.update(ftimeline.now, 'SW: Pain DoT', damage*2, '#C52D2D')
        fmob_hp -= damage*2
        print(f'Mob HP: {fmob_hp}.')
    else:
        print(f'SW: Pain DoT hit for {damage} at {ftimeline.now:.2f}s.')
        flog.update(ftimeline.now, 'SW: Pain DoT', damage, '#C52D2D')
        fmob_hp -= damage
        print(f'Mob HP: {fmob_hp}.')
    # This sets when the next dot hit will occur.
    if ftimeline.now + fpain_dot.dot_hit_interval <= ftimeline.pain_dot_end:
        ftimeline.pain_dot_hit = ftimeline.now + fpain_dot.dot_hit_interval
    else:
        fpain_dot.last_hit_coeff = (ftimeline.pain_dot_end - ftimeline.now)/fpain_dot.dot_hit_interval
        ftimeline.pain_dot_last_hit = ftimeline.pain_dot_end
        ftimeline.pain_dot_hit = float('inf')
    return fmob_hp, ftimeline, fpain_dot, flog


def pain_last_dot_attack(fmob_hp, ftimeline, fpain_dot, flog):
    """Adjusts timeline and hitpoints after a SW: Pain DoT hit."""
    crit_boolean = random.choices([True, False], weights=[crit_chance, 1-crit_chance])[0]
    if ftimeline.now <= ftimeline.schism_debuff_end:
        schism_buff = True
    else:
        schism_buff = False
    damage = int(pain_dd.spell_damage*(1+versatility_percent)*(1+schism_buff*0.4)*fpain_dot.last_hit_coeff)
    if crit_boolean:
        print(f'SW: Pain DoT crit for {damage*2} at {ftimeline.now:.2f}s.')
        flog.update(ftimeline.now, 'SW: Pain DoT', damage*2, '#C52D2D')
        fmob_hp -= damage*2
        print(f'Mob HP: {fmob_hp}.')
    else:
        print(f'SW: Pain DoT hit for {damage} at {ftimeline.now:.2f}s.')
        flog.update(ftimeline.now, 'SW: Pain DoT', damage, '#C52D2D')
        fmob_hp -= damage
        print(f'Mob HP: {fmob_hp}.')
    ftimeline.pain_dot_end = 0
    ftimeline.pain_dot_last_hit = float('inf')
    return fmob_hp, ftimeline, flog


def penance_attack(fmob_hp, ftimeline, fpenance, flog):
    """Adjusts timeline and hitpoints after a Penance attack."""
    crit_boolean = random.choices([True, False], weights=[crit_chance, 1-crit_chance])[0]
    if ftimeline.now <= ftimeline.schism_debuff_end:
        schism_buff = True
    else:
        schism_buff = False
    damage = int(fpenance.hit_damage*(1+versatility_percent)*(1+schism_buff*0.4))
    if crit_boolean:
        print(f'Penance crit for {damage*2} at {ftimeline.now:.2f}s.')
        flog.update(ftimeline.now, 'Penance', damage*2, '#F2FF00')
        fmob_hp -= damage*2
        print(f'Mob HP: {fmob_hp}.')
    else:
        print(f'Penance hit for {damage} at {ftimeline.now:.2f}s.')
        flog.update(ftimeline.now, 'Penance', damage, '#F2FF00')
        fmob_hp -= damage
        print(f'Mob HP: {fmob_hp}.')
    if fpenance.hit_count == 1:
        ftimeline.penance_off_cd = ftimeline.now + fpenance.cooldown
    if fpenance.hit_count < 3:
        ftimeline.penance_hit = ftimeline.now + fpenance.hit_interval
    else:
        ftimeline.penance_hit = float('inf')
        ftimeline = next_spell(ftimeline)
        fpenance.hit_count = 0
    fpenance.hit_count += 1
    return fmob_hp, ftimeline, fpenance, flog


def solace_attack(fmob_hp, ftimeline, flog):
    """Adjusts timeline and hitpoints after a Solace attack."""
    crit_boolean = random.choices([True, False], weights=[crit_chance, 1-crit_chance])[0]
    if ftimeline.now <= ftimeline.schism_debuff_end:
        schism_buff = True
    else:
        schism_buff = False
    damage = int(solace.spell_damage*(1+versatility_percent)*(1+schism_buff*0.4))
    if crit_boolean:
        print(f'Solace crit for {damage*2} at {ftimeline.now:.2f}s.')
        flog.update(ftimeline.now, 'Solace', damage*2, '#3A3F89')
        fmob_hp -= damage*2
        print(f'Mob HP: {fmob_hp}.')
    else:
        print(f'Solace hit for {damage} at {ftimeline.now:.2f}s.')
        flog.update(ftimeline.now, 'Solace', damage, '#3A3F89')
        fmob_hp -= damage
        print(f'Mob HP: {fmob_hp}.')
    ftimeline.solace_hit = float('inf')
    ftimeline.solace_off_cd = ftimeline.now + solace.cooldown
    ftimeline.gcd_end = ftimeline.now + global_cd.cast_time
    return fmob_hp, ftimeline, flog


def divine_star_attack(fmob_hp, ftimeline, fdivine_star, flog):
    """Adjusts timeline and hitpoints after a Divine Star attack."""
    crit_boolean = random.choices([True, False], weights=[crit_chance, 1 - crit_chance])[0]
    if ftimeline.now <= ftimeline.schism_debuff_end:
        schism_buff = True
    else:
        schism_buff = False
    damage = int(fdivine_star.hit_damage * (1 + versatility_percent) * (1 + schism_buff * 0.4))
    if crit_boolean:
        print(f'Divine Star crit for {damage * 2} at {ftimeline.now:.2f}s.')
        flog.update(ftimeline.now, 'Divine Star', damage*2, '#B59C66')
        fmob_hp -= damage * 2
        print(f'Mob HP: {fmob_hp}.')
    else:
        print(f'Divine Star hit for {damage} at {ftimeline.now:.2f}s.')
        flog.update(ftimeline.now, 'Divine Star', damage, '#B59C66')
        fmob_hp -= damage
        print(f'Mob HP: {fmob_hp}.')
    if fdivine_star.hit_count == 1:
        ftimeline.divine_star_off_cd = ftimeline.now + fdivine_star.cooldown
        ftimeline.gcd_end = ftimeline.now + global_cd.cooldown
        # This is fairly arbitrary. Divine Star goes some distance and then turns around and hits everything again on
        # the way back. I'll just estimate that the first hit is instantaneous and the second occurs 1.5 seconds later.
        # Haste seems to have no effect on this spell.
        ftimeline.divine_star_hit = ftimeline.now + 1.5
    else:
        ftimeline.divine_star_hit = float('inf')
        fdivine_star.hit_count = 0
    fdivine_star.hit_count += 1
    return fmob_hp, ftimeline, fdivine_star, flog


def smite_attack(fmob_hp, ftimeline, flog):
    """Adjusts timeline and hitpoints after a Schism attack."""
    crit_boolean = random.choices([True, False], weights=[crit_chance, 1-crit_chance])[0]
    if ftimeline.now <= ftimeline.schism_debuff_end:
        schism_buff = True
    else:
        schism_buff = False
    damage = int(smite.spell_damage*(1+versatility_percent)*(1+schism_buff*0.4))
    if crit_boolean:
        print(f'Smite crit for {damage*2} at {ftimeline.now:.2f}s.')
        flog.update(ftimeline.now, 'Smite', damage*2, '#F4F3E9')
        fmob_hp -= damage*2
        print(f'Mob HP: {fmob_hp}.')
    else:
        print(f'Smite hit for {damage} at {ftimeline.now:.2f}s.')
        flog.update(ftimeline.now, 'Smite', damage, '#F4F3E9')
        fmob_hp -= damage
        print(f'Mob HP: {fmob_hp}.')
    ftimeline.smite_hit = float('inf')
    ftimeline = next_spell(ftimeline)
    return fmob_hp, ftimeline, flog


def next_time_stop():
    """Determines next value for timeline.now"""
    # Values that default to zero can't be included in the list or they'll be the min value every time.
    events_list = [timeline.schism_hit, timeline.pain_dd_hit, timeline.gcd_end, timeline.smite_hit,
                   timeline.pain_dot_hit, timeline.pain_dot_last_hit, timeline.penance_hit, timeline.solace_hit,
                   timeline.divine_star_hit]
    return min(events_list)


def next_spell(ftimeline):
    """After certain spells are cast or the GCD expires, this determines which spell should be cast next."""
    if ftimeline.now >= ftimeline.schism_off_cd:
        ftimeline.schism_hit = ftimeline.now + schism.cast_time
    elif ftimeline.now >= ftimeline.pain_dot_end:
        ftimeline.pain_dd_hit = ftimeline.now
    elif ftimeline.now >= ftimeline.penance_off_cd:
        ftimeline.penance_hit = ftimeline.now
    elif ftimeline.now >= ftimeline.solace_off_cd:
        ftimeline.solace_hit = ftimeline.now
    elif ftimeline.now >= ftimeline.divine_star_off_cd:
        ftimeline.divine_star_hit = ftimeline.now
    else:
        ftimeline.smite_hit = ftimeline.now + smite.cast_time
    return ftimeline


def execute_time_stop(fmob_hp, ftimeline, fpain_dot, fpenance, fdivine_star, flog):
    """Given a timestop, this determines which action should be taken."""
    if ftimeline.now == ftimeline.pain_dot_hit:
        fmob_hp, ftimeline, fpain_dot, flog = pain_dot_attack(fmob_hp, ftimeline, fpain_dot, flog)
    elif ftimeline.now == ftimeline.pain_dot_last_hit:
        fmob_hp, ftimeline, flog = pain_last_dot_attack(fmob_hp, ftimeline, fpain_dot, flog)
    elif ftimeline.now == ftimeline.divine_star_hit:
        fmob_hp, ftimeline, fdivine_star, flog = divine_star_attack(fmob_hp, ftimeline, fdivine_star, flog)
    elif ftimeline.now == ftimeline.schism_hit:
        fmob_hp, ftimeline, flog = schism_attack(fmob_hp, ftimeline, flog)
    elif ftimeline.now == ftimeline.pain_dd_hit:
        fmob_hp, ftimeline, flog = pain_dd_attack(fmob_hp, ftimeline, flog)
    elif ftimeline.now == ftimeline.gcd_end:
        ftimeline.gcd_end = float('inf')
        ftimeline = next_spell(ftimeline)
    elif ftimeline.now == ftimeline.smite_hit:
        fmob_hp, ftimeline, flog = smite_attack(fmob_hp, ftimeline, flog)
    elif ftimeline.now == ftimeline.penance_hit:
        fmob_hp, ftimeline, fpenance, flog = penance_attack(fmob_hp, ftimeline, fpenance, flog)
    elif ftimeline.now == ftimeline.solace_hit:
        fmob_hp, ftimeline, flog = solace_attack(fmob_hp, ftimeline, flog)
    return fmob_hp, ftimeline, fpain_dot, fpenance, fdivine_star, flog


def kill_one(ftimeline, fmob_num, fpain_dot, fpenance, fdivine_star, flog):
    mob_hp = int(random.randrange(mob_min_hp, mob_max_hp+1))
    print(f'Mob {fmob_num} HP: {mob_hp}.')
    ftimeline = next_spell(ftimeline)
    while mob_hp > 0:
        ftimeline.now = next_time_stop()
        mob_hp, ftimeline, fpain_dot, fpenance, fdivine_star, flog = execute_time_stop(mob_hp, ftimeline, fpain_dot,
                                                                                       fpenance, fdivine_star, flog)
    print(f'Mob {fmob_num} died at {ftimeline.now:.2f}.')
    return ftimeline, fmob_num, fpain_dot, fpenance, fdivine_star, flog


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
solace = Spells(0.829, 5.11, 0, 12)
pain_dot = Dots(0.992, 1.31, 16, 2, 0, 0)
penance = Channeled(1.2, 0.726, 3, 2, 9)
divine_star = Star(0.8, 0, 15)

timeline = Timeline()
log = Log()
mob_number = 1

mob_min_hp = 300000
mob_max_hp = 300000

print(f'Haste: {haste_percent:.2%}')
print(f'Crit: {crit_chance:.2%}')
print(f'Mastery: {mastery_percent:.2%}')
print(f'Versatility: {versatility_percent:.2%}\n')

timeline, mob_number, pain_dot, penance, divine_star, log = kill_one(timeline, mob_number, pain_dot, penance,
                                                                     divine_star, log)
print(f'There were {len(log.damage_list)} attacks.')

app = dash.Dash(__name__)

# This is the really low level way of doing it, but I don't know how to add a second trace in this way and I need to add
# multiple traces for a legend because I want to legend to show which spell is which bar color.
fig_dict = {'data': [{'type': 'bar',
                      'x': log.time_list,
                      'y': log.damage_list,
                      'width': .3,
                      'marker': {'line': {'width': 1}, 'color': log.color_list}}],
            'layout': {'showlegend': True}}

fig = go.Figure(fig_dict)
# At this point, you can fig.add_trace or something of the like.

app.layout = html.Div(children=[html.H1(children='Hello!'),
                                dcc.Graph(id='example-graph',
                                          figure=fig)])

if __name__ == '__main__':
    app.run_server(debug=True)
