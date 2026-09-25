import re, datetime, random
from jinja2 import Environment, FileSystemLoader
src=open("app.py",encoding="utf-8").read()
m=re.search(r'^ADMIN_HTML = (r?)"""(.*?)"""\n',src,re.S|re.M)
tpl=Environment(loader=FileSystemLoader("assessment/templates")).from_string(m.group(2))
class L(dict): __getattr__=dict.get
now=datetime.datetime.now()
perms={k:True for k in ["view_knowledge","edit_knowledge","view_advisors","edit_advisors",
 "edit_voice","edit_onboarding_data","view_participant_links","edit_participant_links",
 "view_conversation_log","edit_conversation_log","edit_biometric","edit_settings",
 "edit_learning","manage_admins"]}
LOREM=("The mistake most clinical leaders make is waiting to be noticed. "*14)
docs=[L(id=i,title=f"Doc {i}",source=f"doc{i}.pdf",chunk_count=42,uploaded_at=now) for i in range(30)]
feedback=[L(id=i,created_at=now,rating=random.choice(["up","down",None]),persona="Alan Friedman",
   user_message=LOREM[:600],bot_reply=LOREM,comment=LOREM[:300],attachment_info="",
   approved_for_learning=False) for i in range(25)]
links=[L(id=i,token="tok%02d"%i,label=f"Participant {i}",first_name="Jane",email="j@x.com",
   advisor_slug="alan-friedman" if i%2 else "",enabled=True,created_at=now,last_used_at=now) for i in range(12)]
VS=L(filename="v.webm",size_bytes=3_000_000,consent_given=True,consent_note="",provider="elevenlabs",
     provider_voice_id="v1",voice_mode="auto",voice_stability=0.5,voice_similarity_boost=0.75,
     voice_style=0.0,voice_speaker_boost=True,voice_speed=1.0,uploaded_at=now)
def mkadv(slug,name):
    return L(slug=slug,name=name,has_photo=True,no_photo=False,scheduling_url="",
      show_scheduling_override=None,show_avatar_override=None,allow_materials_override=None,
      personality_override=None,portal_token="t"*32,client_bio=LOREM[:200],expertise=LOREM[:200],
      briefings=[L(when="2026-09-01",advisor=name,participant="X",summary=LOREM,emailed=True) for _ in range(3)],
      documents=[],personality={"scores":{"openness":5.5},"completed_at":now},
      personality_result=({"answers":{},"scores":{},"completed_at":now} if slug=="david-nash" else None),
      behavioral={"scores":{"communication":4.0},"completed_at":now},
      feedback_360=L(id=1,filename="360.pdf",size_bytes=2_000_000,uploaded_at=now),
      voice_sample=VS,suggested_bio=LOREM[:200],internal_only=(slug=="alan-friedman"))
advisors=[mkadv("alan-friedman","Alan Friedman"),mkadv("bruce-gewertz","Bruce Gewertz, MD"),
          mkadv("david-nash","David Nash"),mkadv("eddie-erlandson","Eddie Erlandson, MD")]
by_adv={a["slug"]:[l for l in links if l["advisor_slug"]==a["slug"]] for a in advisors}
by_adv[""]=[l for l in links if not l["advisor_slug"]]
TABS=("overview","activity","advisors","biometric","knowledge","users","settings","diagnostics")
def ctx(tab):
    return dict(active_tab=tab, admin_tabs=TABS,
     cfg={"persona_name":"J3P Advisor","favicon_url":"/f","logo_url":"/l","avatar_url":"/a","max_upload_mb":100},
     docs=docs, feedback_rows=(feedback if tab=="activity" else []),
     settings={"avatar_name":"","require_login":False,"auto_learning":False,"avatar_no_photo":True,"default_scheduling_url":""},
     mail_ready=True,avatar_custom=False,elevenlabs_configured=True,default_persona_voice_sample=VS,
     default_persona_slug="__default_persona__",
     advisors=(advisors if tab in ("advisors","knowledge") else advisors),
     owners={},advisor_map={},doc_owner_labels={},
     advisor_names={a["slug"]:a["name"] for a in advisors},advisor_docs={},initials_for=lambda n:"AF",
     personality_summary_tag=lambda s:"Balanced",behavioral_summary_tag=lambda s:"Strong",
     participant_links=links,participant_links_by_advisor=by_adv,
     voice_archives={'alan-friedman':[L(id=1,filename='voice-sample.webm',size_bytes=2_800_000,consent_given=True,reason='replaced by a new recording',archived_at=now)]},
     biometric_files=[],avatar_version=1,avatar_max_mb=25,
     learning_runs=[L(when="x",trigger="manual",approved=1,skipped=0,detail="")] if tab=="activity" else [],
     briefings=[],archived_runs=3,learning_interval=24,app_version="2026-09-16-b",
     locations={},acks={},personality_notes={},personality_summary={},personality_tips={},
     base_url="https://web-production-901d85.up.railway.app",stats={"up":30,"down":4,"total":34},
     rag_ready=True,db_ok=True,emb_ok=True,log_filter="all",
     log_personas=(["Alan Friedman"] if tab=="activity" else []),log_persona="",log_limit=25,
     admin_identity={"name":"Owner","email":"o@x","role":"owner","is_master":False},
     admin_perms=perms,admin_users=[L(id=1,name='Kristen Woods',email='k@j3p.health',role='admin',enabled=True,created_at=now,last_login_at=now,advisor_scope='alan-friedman'),L(id=2,name='Owner',email='a@j3p.health',role='owner',enabled=True,created_at=now,last_login_at=now,advisor_scope='')],app_build_notes='test notes',show_timing=False,short_location=(lambda v: (v or '').split(',')[0]),show_personality_col=False,show_tips_col=False,show_location_col=True,research_query='physician burnout',research_sources=['pubmed','openalex'],research_results=[L(source='PubMed',title='Burnout among academic physician leaders',authors=['Shanafelt TD','Noseworthy JH'],journal='Academic Medicine',year='2024',abstract='BACKGROUND: Burnout is widespread. RESULTS: Autonomy predicted lower burnout.',doi='10.1097/ACM.5',url='https://pubmed.ncbi.nlm.nih.gov/38912345/',cited_by=0,open_access=False),L(source='OpenAlex',title='Team dynamics in surgery',authors=['Rogers S'],journal='BMJ',year='2023',abstract='Rebuilt abstract text.',doi='10.1000/x',url='https://doi.org/10.1000/x',cited_by=42,open_access=True)],first_request_boot_ms=3000,
 diag={'persistent_conns':True,'reuse_shared_conn':False,'db_host':'roundhouse.proxy.rlwy.net','db_private':False,'voice':{'elevenlabs_key_set':True,'with_sample':{'alan-friedman':{'name':'Alan Friedman','consent_given':True,'cloned':True,'voice_mode':'participant_choice','size_kb':2929}},'advisors_without_sample':['bruce-gewertz']},
 'page_timings':[L(label='/admin?tab=advisors',total_ms=3120,at=now,phases=[('list_advisors',180),('advisor detail maps',1450),('participant links',620),('documents',410),('template render',340)])],'chat_timings':[L(total_ms=14230,at=now,phases=[('request parsed + attachments',12),('conversation history',48),('knowledge retrieval',610),('prompt assembly',3),('model call',13400),('reply post-processing',160)])],'grounding':{'checked':42,'grounded':31,'weak':8,'ungrounded':3,'no_kb':0,'recent':[L(score=0.31,question='How do I handle a difficult chair?',advisor='alan-friedman',verdict='not supported by the knowledge base',sources=[])]}},url_for=lambda ep,**kw:"/admin?tab="+kw.get("tab","") if ep=="admin_dashboard" else "/admin/x",
     get_flashed_messages=lambda:[])
print(f"{'tab':<12}{'KB':>8}   panes rendered")
for t in TABS:
    out=tpl.render(**ctx(t))
    n=out.count('class="tab-pane"')
    print(f"{t:<12}{len(out)/1024:>8.0f}   {n}")
