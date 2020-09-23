import random
from flask import Blueprint
import plotly.graph_objects as go
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output


wowsim_bp = Blueprint('wowsim_bp', __name__,
                      static_folder='static',
                      template_folder='templates',
                      static_url_path='/wowsim/static')


def figure_maker(fig_name, log_name, bar_color):
    """Creates plotly figure dictionaries"""
    return {'type': 'bar',
            'name': fig_name,
            'x': log_name.time_list,
            'y': log_name.damage_list,
            'width': .4,
            'marker': {'line': {'width': 1}, 'color': bar_color}}


def make_dash(intellect, crit_rating, haste_rating, mastery_rating, versatility_rating):
    """Creates a new simulation timeline, figure, and DPS from the given stats."""
    class Spells:
        """Creates stats for direct damage spells"""

        def __init__(self, sp_weight, sp_bias, cast_time, cooldown):
            self.spell_damage = sp_weight * intellect + sp_bias
            self.cast_time = cast_time / (1 + haste_percent)
            self.cooldown = cooldown

    class Dots:
        """Creates stats for damage-over-time spells"""

        def __init__(self, sp_weight, sp_bias, dot_duration, hit_interval, cast_time, cooldown):
            self.dot_hit_damage = (sp_weight * intellect + sp_bias) / (dot_duration / hit_interval)
            self.dot_hit_interval = hit_interval / (1 + haste_percent)
            self.dot_duration = dot_duration
            self.cast_time = cast_time / (1 + haste_percent)
            self.cooldown = cooldown
            self.last_hit_coeff = 0

    class Channeled:
        """Creates stats for channeled spells"""

        def __init__(self, sp_weight, sp_bias, hits, channel_duration, cooldown):
            self.hit_damage = (sp_weight * intellect + sp_bias) / hits
            self.hit_interval = (channel_duration / (1 + haste_percent)) / hits
            self.cooldown = cooldown
            self.hit_count = 1

    class Star:
        """Creates stats for Divine Star"""

        def __init__(self, sp_weight, sp_bias, cooldown):
            self.hit_damage = (sp_weight * intellect + sp_bias) / 2
            self.cooldown = cooldown
            self.hit_count = 1

    class Log:
        """This is for logging data that will be passed to the timeline graph."""

        def __init__(self):
            self.time_list = []
            self.damage_list = []

        def update(self, time, damage):
            self.time_list.append(time)
            self.damage_list.append(damage)

    class Logs:
        """A class to hold all the logs."""

        def __init__(self):
            self.schism_log = Log()
            self.pain_log = Log()
            self.smite_log = Log()
            self.solace_log = Log()
            self.penance_log = Log()
            self.divine_star_log = Log()

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
        crit_boolean = random.choices([True, False], weights=[crit_chance, 1 - crit_chance])[0]
        if ftimeline.now <= ftimeline.schism_debuff_end:
            schism_buff = True
        else:
            schism_buff = False
        damage = int(schism.spell_damage * (1 + versatility_percent) * (1 + schism_buff * 0.4))
        if crit_boolean:
            # print(f'Schism crit for {damage * 2} at {ftimeline.now:.2f}s.')
            flog.schism_log.update(ftimeline.now, damage * 2)
            fmob_hp -= damage * 2
            # print(f'Mob HP: {fmob_hp}.')
        else:
            # print(f'Schism hit for {damage} at {ftimeline.now:.2f}s.')
            flog.schism_log.update(ftimeline.now, damage)
            fmob_hp -= damage
            # print(f'Mob HP: {fmob_hp}.')
        ftimeline.schism_hit = float('inf')
        ftimeline.schism_off_cd = ftimeline.now + schism.cooldown
        ftimeline.schism_debuff_end = ftimeline.now + 9
        ftimeline = next_spell(ftimeline)
        return fmob_hp, ftimeline, flog

    def pain_dd_attack(fmob_hp, ftimeline, flog):
        """Adjusts timeline and hitpoints after the direct damage portion of SW: Pain."""
        crit_boolean = random.choices([True, False], weights=[crit_chance, 1 - crit_chance])[0]
        if ftimeline.now <= ftimeline.schism_debuff_end:
            schism_buff = True
        else:
            schism_buff = False
        damage = int(pain_dd.spell_damage * (1 + versatility_percent) * (1 + schism_buff * 0.4))
        if crit_boolean:
            # print(f'SW: Pain DD crit for {damage * 2} at {ftimeline.now:.2f}s.')
            flog.pain_log.update(ftimeline.now, damage * 2)
            fmob_hp -= damage * 2
            # print(f'Mob HP: {fmob_hp}.')
        else:
            # print(f'SW: Pain DD hit for {damage} at {ftimeline.now:.2f}s.')
            flog.pain_log.update(ftimeline.now, damage)
            fmob_hp -= damage
            # print(f'Mob HP: {fmob_hp}.')
        ftimeline.pain_dd_hit = float('inf')
        ftimeline.pain_dot_end = ftimeline.now + pain_dot.dot_duration
        ftimeline.pain_dot_hit = ftimeline.now + pain_dot.dot_hit_interval
        ftimeline.gcd_end = ftimeline.now + global_cd.cast_time
        return fmob_hp, ftimeline, flog

    def pain_dot_attack(fmob_hp, ftimeline, fpain_dot, flog):
        """Adjusts timeline and hitpoints after a SW: Pain DoT hit."""
        crit_boolean = random.choices([True, False], weights=[crit_chance, 1 - crit_chance])[0]
        if ftimeline.now <= ftimeline.schism_debuff_end:
            schism_buff = True
        else:
            schism_buff = False
        damage = int(pain_dd.spell_damage * (1 + versatility_percent) * (1 + schism_buff * 0.4))
        if crit_boolean:
            # print(f'SW: Pain DoT crit for {damage * 2} at {ftimeline.now:.2f}s.')
            flog.pain_log.update(ftimeline.now, damage * 2)
            fmob_hp -= damage * 2
            # print(f'Mob HP: {fmob_hp}.')
        else:
            # print(f'SW: Pain DoT hit for {damage} at {ftimeline.now:.2f}s.')
            flog.pain_log.update(ftimeline.now, damage)
            fmob_hp -= damage
            # print(f'Mob HP: {fmob_hp}.')
        # This sets when the next dot hit will occur.
        if ftimeline.now + fpain_dot.dot_hit_interval <= ftimeline.pain_dot_end:
            ftimeline.pain_dot_hit = ftimeline.now + fpain_dot.dot_hit_interval
        else:
            fpain_dot.last_hit_coeff = (ftimeline.pain_dot_end - ftimeline.now) / fpain_dot.dot_hit_interval
            ftimeline.pain_dot_last_hit = ftimeline.pain_dot_end
            ftimeline.pain_dot_hit = float('inf')
        return fmob_hp, ftimeline, fpain_dot, flog

    def pain_last_dot_attack(fmob_hp, ftimeline, fpain_dot, flog):
        """Adjusts timeline and hitpoints after a SW: Pain DoT hit."""
        crit_boolean = random.choices([True, False], weights=[crit_chance, 1 - crit_chance])[0]
        if ftimeline.now <= ftimeline.schism_debuff_end:
            schism_buff = True
        else:
            schism_buff = False
        damage = int(
            pain_dd.spell_damage * (1 + versatility_percent) * (1 + schism_buff * 0.4) * fpain_dot.last_hit_coeff)
        if crit_boolean:
            # print(f'SW: Pain DoT crit for {damage * 2} at {ftimeline.now:.2f}s.')
            flog.pain_log.update(ftimeline.now, damage * 2)
            fmob_hp -= damage * 2
            # print(f'Mob HP: {fmob_hp}.')
        else:
            # print(f'SW: Pain DoT hit for {damage} at {ftimeline.now:.2f}s.')
            flog.pain_log.update(ftimeline.now, damage)
            fmob_hp -= damage
            # print(f'Mob HP: {fmob_hp}.')
        ftimeline.pain_dot_end = 0
        ftimeline.pain_dot_last_hit = float('inf')
        return fmob_hp, ftimeline, flog

    def penance_attack(fmob_hp, ftimeline, fpenance, flog):
        """Adjusts timeline and hitpoints after a Penance attack."""
        crit_boolean = random.choices([True, False], weights=[crit_chance, 1 - crit_chance])[0]
        if ftimeline.now <= ftimeline.schism_debuff_end:
            schism_buff = True
        else:
            schism_buff = False
        damage = int(fpenance.hit_damage * (1 + versatility_percent) * (1 + schism_buff * 0.4))
        if crit_boolean:
            # print(f'Penance crit for {damage * 2} at {ftimeline.now:.2f}s.')
            flog.penance_log.update(ftimeline.now, damage * 2)
            fmob_hp -= damage * 2
            # print(f'Mob HP: {fmob_hp}.')
        else:
            # print(f'Penance hit for {damage} at {ftimeline.now:.2f}s.')
            flog.penance_log.update(ftimeline.now, damage)
            fmob_hp -= damage
            # print(f'Mob HP: {fmob_hp}.')
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
        crit_boolean = random.choices([True, False], weights=[crit_chance, 1 - crit_chance])[0]
        if ftimeline.now <= ftimeline.schism_debuff_end:
            schism_buff = True
        else:
            schism_buff = False
        damage = int(solace.spell_damage * (1 + versatility_percent) * (1 + schism_buff * 0.4))
        if crit_boolean:
            # print(f'Solace crit for {damage * 2} at {ftimeline.now:.2f}s.')
            flog.solace_log.update(ftimeline.now, damage * 2)
            fmob_hp -= damage * 2
            # print(f'Mob HP: {fmob_hp}.')
        else:
            # print(f'Solace hit for {damage} at {ftimeline.now:.2f}s.')
            flog.solace_log.update(ftimeline.now, damage)
            fmob_hp -= damage
            # print(f'Mob HP: {fmob_hp}.')
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
            # print(f'Divine Star crit for {damage * 2} at {ftimeline.now:.2f}s.')
            flog.divine_star_log.update(ftimeline.now, damage * 2)
            fmob_hp -= damage * 2
            # print(f'Mob HP: {fmob_hp}.')
        else:
            # print(f'Divine Star hit for {damage} at {ftimeline.now:.2f}s.')
            flog.divine_star_log.update(ftimeline.now, damage)
            fmob_hp -= damage
            # print(f'Mob HP: {fmob_hp}.')
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
        crit_boolean = random.choices([True, False], weights=[crit_chance, 1 - crit_chance])[0]
        if ftimeline.now <= ftimeline.schism_debuff_end:
            schism_buff = True
        else:
            schism_buff = False
        damage = int(smite.spell_damage * (1 + versatility_percent) * (1 + schism_buff * 0.4))
        if crit_boolean:
            # print(f'Smite crit for {damage * 2} at {ftimeline.now:.2f}s.')
            flog.smite_log.update(ftimeline.now, damage * 2)
            fmob_hp -= damage * 2
            # print(f'Mob HP: {fmob_hp}.')
        else:
            # print(f'Smite hit for {damage} at {ftimeline.now:.2f}s.')
            flog.smite_log.update(ftimeline.now, damage)
            fmob_hp -= damage
            # print(f'Mob HP: {fmob_hp}.')
        ftimeline.smite_hit = float('inf')
        ftimeline = next_spell(ftimeline)
        return fmob_hp, ftimeline, flog

    def next_time_stop():
        """Determines next value for timeline.now"""
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
        mob_hp = 500000
        # print(f'Mob {fmob_num} HP: {mob_hp}.')
        ftimeline = next_spell(ftimeline)
        while mob_hp > 0:
            ftimeline.now = next_time_stop()
            mob_hp, ftimeline, fpain_dot, fpenance, fdivine_star, flog = execute_time_stop(mob_hp, ftimeline, fpain_dot,
                                                                                           fpenance, fdivine_star, flog)
        # print(f'Mob {fmob_num} died at {ftimeline.now:.2f}.')
        return ftimeline, fmob_num, fpain_dot, fpenance, fdivine_star, flog

    haste_percent = 0.04
    crit_chance = crit_rating*0.1768/1273
    haste_percent = haste_rating*0.0696/473
    mastery_percent = mastery_rating*0.1343/716
    versatility_percent = versatility_rating*0.0389/331

    schism = Spells(1.29, 7.77, 1.5, 24)
    global_cd = Spells(0, 0, 1.5, 0)
    pain_dd = Spells(0.165, 0.858, 0, 0)
    smite = Spells(0.57, 3.26, 1.5, 0)
    solace = Spells(0.829, 5.11, 0, 12)
    pain_dot = Dots(0.992, 1.31, 16, 2, 0, 0)
    penance = Channeled(1.2, 0.726, 3, 2, 9)
    divine_star = Star(0.8, 0, 15)
    timeline = Timeline()
    logs = Logs()
    mob_number = 1

    timeline, mob_number, pain_dot, penance, divine_star, logs = kill_one(timeline, mob_number, pain_dot, penance,
                                                                          divine_star, logs)
    collective_fig = {'data': [figure_maker('Schism', logs.schism_log, '#2F2F2F'),
                               figure_maker('Solace', logs.solace_log, 'orange'),
                               figure_maker('Smite', logs.smite_log, '#589B9B'),
                               figure_maker('Penance', logs.penance_log, 'yellow'),
                               figure_maker('Divine Star', logs.divine_star_log, 'white'),
                               figure_maker('SW: Pain', logs.pain_log, '#797a7e')],
                      'layout': {'showlegend': True, 'paper_bgcolor': '#3d3d3d', 'plot_bgcolor': '#D6CCB4',
                                 'legend': {'font': {'family': 'Shadows Into Light', 'color': '#D8E7EF', 'size': 24},
                                            'orientation': 'v'}}}
    fig = go.Figure(collective_fig)
    fig.update_layout(barmode='stack', font_color='#D6CCB4',
                      xaxis={'title': {'text': 'Time (Seconds)', 'font': {'family': 'Shadows Into Light', 'size': 24}}},
                      yaxis={'title': {'text': 'Damage', 'font': {'family': 'Shadows Into Light', 'size': 24}}},
                      title={'text': 'Timeline of Spell Hits', 'xref': 'paper', 'x': 0.5,
                             'font': {'family': 'Shadows Into Light', 'size': 34}})
    fig.update_traces(marker={'line': {'color': 'black', 'width': 0}})
    results = ['Time to do 500k damage: ', html.Span(className='time_taken', children=f'{timeline.now:.02f}'),
               ' seconds',
               html.Br(),
               'Average DPS: ', html.Span(className='time_taken', children=f'{500000/timeline.now:,.02f}')]

    return fig, results


def initial_layout(intel, crit, haste, mastery, versatility):
    fig, results = make_dash(intel, crit, haste, mastery, versatility)
    return html.Div(children=[html.H1(className='head',
                                      children='Disc Priest Damage Simulator'),
                              html.Div(className='settings',
                                       id='settings',
                                       children=['Intellect: ', dcc.Input(className='inputs', id='intellect',
                                                                          value=7000, type='number', debounce=True),
                                                 ' Crit Rating: ', dcc.Input(className='inputs', id='crit',
                                                                             value=1000,
                                                                             type='number', debounce=True),
                                                 ' Haste Rating: ', dcc.Input(className='inputs', id='haste',
                                                                              value=1000, type='number',
                                                                              debounce=True),
                                                 ' Mastery Rating: ', dcc.Input(className='inputs', id='mastery',
                                                                                value=1000, type='number',
                                                                                debounce=True),
                                                 ' Versatility Rating: ', dcc.Input(className='inputs',
                                                                                    id='versatility', value=500,
                                                                                    type='number', debounce=True)]),
                              html.Div(className='results',
                                       id='results',
                                       children=results),
                              dcc.Graph(id='example-graph', figure=fig),
                              html.Div(className='about',
                                       children=[html.H1('About'),
                                                 'This app will simulate combat undertaken by a level 120 discipline '
                                                 'priest in the Battle for Azeroth expansion of World of Warcraft. It '
                                                 'assists a player in deciding how to gear and distribute their stats '
                                                 'for maximum effect. Spells are prioritized in the following order: '
                                                 'Schism, SW: Pain, Penance, Solace, Divine Star, Smite. SW: Pain is '
                                                 'only cast when it is no longer in effect. The rest are cast when off '
                                                 'cooldown and according to their priority. This app does not account '
                                                 'for many talent choices. Note that there is randomness in critical '
                                                 'hits. Thus, multiple runs with identical stats will likely render '
                                                 'different results. Also note that this app does not simulate the '
                                                 'effects of Azerite traits, Corruptions, and a host of trinkets. As '
                                                 'the variety and magnitudes of such effects are expansive and the end '
                                                 'of this expansion is imminent, I have no plans of going to the '
                                                 'effort of adding them.',
                                                 html.H1('Technical Info'),
                                                 'The app requires merging multiple overlapping timelines of events, '
                                                 'finding the next event, creating new events at appropriate time '
                                                 'stops, erasing past events, calculating the magnitude of spell hits, '
                                                 'simulating randomness, and determining the next attack to be '
                                                 'carried out based on those timelines. The page is generated by Dash '
                                                 'which is akin to a merging of Plotly with Flask. The backend was '
                                                 'written in Python. For deployment, the '
                                                 'Dash app was integrated as a directory into a Flask app following '
                                                 'the Flask Application Factory pattern; thus allowing for easy '
                                                 'scalability. The app is hosted on a Google Compute Engine running '
                                                 'Ubuntu 20.04, Nginx, and Gunicorn.'])
                              ]
                    )


@wowsim_bp.route('/wowsim', methods=['GET'])
def create_sim_dash(server):
    """Creates the Wow Sim App dashboard and determines its initial layout."""
    sim_app = dash.Dash(__name__, server=server, routes_pathname_prefix='/wowsim/')
    sim_app.layout = initial_layout(7000, 1000, 1000, 500, 500)

    init_callbacks(sim_app)


def init_callbacks(sim_app):
    @sim_app.callback(
        [Output(component_id='example-graph', component_property='figure'),
         Output(component_id='results', component_property='children')],
        [Input(component_id='intellect', component_property='value'),
         Input(component_id='crit', component_property='value'),
         Input(component_id='haste', component_property='value'),
         Input(component_id='mastery', component_property='value'),
         Input(component_id='versatility', component_property='value')]
    )
    def update_dash(intel, crit, haste, mastery, versatility):
        fig, now = make_dash(intel, crit, haste, mastery, versatility)
        return fig, now
