"""Décisions contextuelles des destinataires fictifs, reproductibles via state.rng."""
from __future__ import annotations


def decide(state, host, params):
    profile = host.phishing
    if profile.get('response') != 'submitted' or not profile.get('human_model'):
        return profile.get('response','submitted')
    model = profile['human_model']
    campaign = next((c for c in state.tool_data.get('gophish',{}).get('campaigns',[]) if c['id']==params.get('gophish_campaign_id')), {})
    template_name = campaign.get('template',{}).get('name','')
    template = next((t for t in state.tool_data.get('gophish',{}).get('templates',[]) if t['name']==template_name),{})
    subject = template.get('subject','').strip().casefold()
    key = state.domain.get('name','') + ':' + host.hostname + ':' + str(host.primary_user)
    memory = state.tool_data.setdefault('human_memory',{}).setdefault(key, {'contacts':0,'subjects':[],'last_minute':None})
    minute = state.environment.get('world_minute',state.tick//3)
    repeated = subject in memory['subjects']
    rapid = memory['last_minute'] is not None and minute-memory['last_minute']<30
    suspicion = min(.9, model.get('suspicion',.1) + memory['contacts']*.08 + (.2 if repeated else 0) + (.12 if rapid else 0))
    report_probability = min(.85, model.get('report_probability',.05) + suspicion*.3)
    submit_probability = max(.02, min(1-report_probability, model.get('submit_probability',.65)*(1-suspicion)))
    roll = state.rng.random()
    response = 'reported' if roll < report_probability else ('submitted' if roll < report_probability+submit_probability else 'ignored')
    memory['contacts'] += 1
    memory['last_minute'] = minute
    if subject not in memory['subjects']: memory['subjects'].append(subject)
    memory['last_response'] = response
    # Le diagnostic détaillé reste dans l'état interne et n'est pas publié par l'API.
    memory['last_suspicion'] = suspicion
    return response
