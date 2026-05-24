"""
=============================================================
  SCHOOL REGISTRAR SYSTEM v3.0
  Python + Streamlit + MongoDB Atlas
=============================================================
  SETUP:
    1. pip install streamlit pandas pymongo dnspython
    2. Create .streamlit/secrets.toml  (see SETUP.md)
    3. streamlit run app.py

  DEFAULT ADMIN:  admin / admin123
  DEFAULT VIEWER: teacher1 / teacher123
=============================================================
"""

import streamlit as st
import pandas as pd
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, date

# ── PAGE CONFIG — must be the very first Streamlit call ───────────
st.set_page_config(page_title="School Registrar System", page_icon="🏫", layout="wide")

# ── ACCOUNTS — edit credentials here ─────────────────────────────
ADMIN_ACCOUNTS  = {"admin": "admin123"}
VIEWER_ACCOUNTS = {"teacher1": "teacher123", "staff1": "staff123"}

# ── CONSTANTS ────────────────────────────────────────────────────
GRADE_LEVELS   = ["Grade 7","Grade 8","Grade 9","Grade 10","Grade 11","Grade 12"]
SUBJECTS       = ["Filipino","English","Mathematics","Science","Araling Panlipunan",
                   "MAPEH","TLE","Values Education","Computer Science","Other"]
QUARTERS       = ["Q1","Q2","Q3","Q4"]
RELIGIONS      = ["Roman Catholic","Islam","Born Again Christian","Iglesia ni Cristo",
                   "Seventh-Day Adventist","Other","Prefer not to say"]
MOTHER_TONGUES = ["Filipino/Tagalog","Cebuano","Ilocano","Hiligaynon",
                   "Waray","Kapampangan","Bicol","Other"]
CATEGORIES_INV = ["Paper & Forms","Writing Supplies","Filing & Storage",
                   "Ink & Toner","Office Equipment","Cleaning Supplies","Other"]
UNITS          = ["pieces","packs","boxes","reams","bottles","sets","units"]
STATUS_OPTS    = ["Pending","Approved","Enrolled","Rejected","Transferred Out"]
APP_TYPES      = ["New Enrollment","Transfer In","Transfer Out","Re-enrollment","Returnee"]

def school_years():
    y = datetime.now().year
    return [f"{i}-{i+1}" for i in range(y+1, y-7, -1)]

# ── DATABASE ─────────────────────────────────────────────────────
@st.cache_resource
def get_db():
    """Cache the DB connection so it isn't recreated on every rerun."""
    client = MongoClient(st.secrets["MONGODB_URI"])
    return client["school_registrar"]

# ── SESSION STATE DEFAULTS ───────────────────────────────────────
_defaults = {
    "logged_in": False, "role": None, "username": "",
    "page_index": 0,
    "edit_student": None, "edit_grade": None,
    "edit_inventory": None, "edit_alumni": None, "edit_enrollment": None,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── HELPERS ──────────────────────────────────────────────────────
def is_admin(): return st.session_state.role == "admin"
def oid(doc):   return str(doc["_id"])

def calc_age(bday_str):
    try:
        b = datetime.strptime(bday_str, "%Y-%m-%d").date()
        t = date.today()
        return t.year - b.year - ((t.month, t.day) < (b.month, b.day))
    except: return "—"

def grade_list_opts(col, extra=None):
    """Return [All, ...existing sections...] for filter dropdowns."""
    vals = sorted(set(s.get(col,"") for s in db["students"].find({},{col:1}) if s.get(col)))
    return ["All"] + (extra or []) + vals


# ═════════════════════════════════════════════════════════════════
#  LOGIN
# ═════════════════════════════════════════════════════════════════
def show_login():
    _, col, _ = st.columns([1,2,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("🏫 School Registrar System")
        st.markdown("---")
        tab_a, tab_v = st.tabs(["🔐 Admin Login", "👁️ Viewer Login"])
        with tab_a:
            st.caption("Full access — add, edit, and delete records.")
            u = st.text_input("Username", key="au")
            p = st.text_input("Password", type="password", key="ap")
            if st.button("Login as Admin", use_container_width=True):
                if ADMIN_ACCOUNTS.get(u) == p:
                    st.session_state.update(logged_in=True, role="admin", username=u, page_index=0)
                    st.rerun()
                else: st.error("Incorrect username or password.")
        with tab_v:
            st.caption("View only — cannot add, edit, or delete.")
            u = st.text_input("Username", key="vu")
            p = st.text_input("Password", type="password", key="vp")
            if st.button("Login as Viewer", use_container_width=True):
                if VIEWER_ACCOUNTS.get(u) == p:
                    st.session_state.update(logged_in=True, role="viewer", username=u, page_index=0)
                    st.rerun()
                else: st.error("Incorrect username or password.")

if not st.session_state.logged_in:
    show_login()
    st.stop()

# ── Connect to DB (only after login) ─────────────────────────────
db            = get_db()
students_col  = db["students"]
alumni_col    = db["alumni"]
grades_col    = db["grades"]
inventory_col = db["inventory"]
enroll_col    = db["enrollments"]

# ═════════════════════════════════════════════════════════════════
#  SIDEBAR — page_index fixes the "stuck on wrong page" bug
# ═════════════════════════════════════════════════════════════════
PAGES = ["🏠 Dashboard","👤 Student Records","🎓 Alumni & Graduates",
         "📋 Enrollment / Transfer","📝 Grade Submission","📦 Office Inventory"]

st.sidebar.title("🏫 Registrar System")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigate to:", PAGES,
                         index=st.session_state.page_index, key="nav")
st.session_state.page_index = PAGES.index(page)   # keep index in sync

st.sidebar.markdown("---")
badge = "🔐 Admin" if is_admin() else "👁️ Viewer"
st.sidebar.markdown(f"**User:** `{st.session_state.username}`  \n**Role:** {badge}")
if st.sidebar.button("🚪 Logout", use_container_width=True):
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.rerun()
st.sidebar.caption("School Registrar System v3.0")

if not is_admin():
    st.info("👁️ **Viewer mode** — contact the administrator to make changes.")


# ═════════════════════════════════════════════════════════════════
#  PAGE 1 — DASHBOARD
# ═════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.title("🏠 Dashboard")
    st.markdown(f"Welcome back, **{st.session_state.username}**!")
    st.markdown("---")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("👤 Students",      students_col.count_documents({}))
    c2.metric("🎓 Alumni",        alumni_col.count_documents({}))
    c3.metric("📋 Pending Apps",  enroll_col.count_documents({"status":"Pending"}))
    c4.metric("📝 Grade Records", grades_col.count_documents({}))
    total_inv = sum(i.get("quantity",0) for i in inventory_col.find())
    c5.metric("📦 Inventory Qty", total_inv)

    st.markdown("---")
    left, right = st.columns(2)

    with left:
        st.subheader("📋 Recently Added Students")
        recent = list(students_col.find().sort("date_added",-1).limit(5))
        if recent:
            for s in recent:
                st.markdown(f"**{s['last_name']}, {s['first_name']}** — {s.get('grade_level','?')} {s.get('section','?')} · SY {s.get('school_year','?')}")
        else: st.info("No students yet.")

        st.subheader("📋 Pending Applications")
        pending = list(enroll_col.find({"status":"Pending"}).limit(5))
        if pending:
            for p in pending:
                st.info(f"📌 **{p['applicant_name']}** — {p['application_type']} › {p['grade_applying']} ({p.get('school_year','?')})")
        else: st.success("✅ No pending applications.")

    with right:
        st.subheader("⚠️ Low Stock Alerts")
        low = list(inventory_col.find({"quantity":{"$lte":5}}))
        if low:
            for item in low:
                st.warning(f"⚠️ **{item['item_name']}** — only **{item['quantity']}** {item['unit']} left")
        else: st.success("✅ All items sufficiently stocked.")


# ═════════════════════════════════════════════════════════════════
#  PAGE 2 — STUDENT RECORDS
# ═════════════════════════════════════════════════════════════════
elif page == "👤 Student Records":
    st.title("👤 Student Records")
    st.markdown("---")

    # ── Filters ──────────────────────────────────────────────────
    with st.expander("🔍 Filter Students", expanded=True):
        fc1,fc2,fc3,fc4,fc5 = st.columns(5)
        f_name    = fc1.text_input("Name or LRN")
        f_grade   = fc2.selectbox("Grade Level", ["All"]+GRADE_LEVELS)
        f_gender  = fc3.selectbox("Gender",      ["All","Male","Female"])
        f_year    = fc4.selectbox("School Year", ["All"]+school_years())
        secs = sorted(set(s.get("section","") for s in students_col.find({},{"section":1}) if s.get("section")))
        f_sec = fc5.selectbox("Section", ["All"]+secs)

    q = {}
    if f_name:  q["$or"] = [{"first_name":{"$regex":f_name,"$options":"i"}},
                              {"last_name": {"$regex":f_name,"$options":"i"}},
                              {"lrn":       {"$regex":f_name,"$options":"i"}}]
    if f_grade  != "All": q["grade_level"]  = f_grade
    if f_gender != "All": q["gender"]       = f_gender
    if f_year   != "All": q["school_year"]  = f_year
    if f_sec    != "All": q["section"]      = f_sec
    students = list(students_col.find(q).sort("last_name",1))

    tabs = ["📋 Student List","🔎 Profile"] + (["➕ Add Student"] if is_admin() else [])
    T = st.tabs(tabs)

    # ── TAB: Student List ────────────────────────────────────────
    with T[0]:
        st.caption(f"Found **{len(students)}** student(s)")
        if not students: st.info("No students match the filter.")
        for s in students:
            sid  = oid(s)
            cols = st.columns([3,2,1,2,2,1,1] if is_admin() else [3,2,1,2,2])
            cols[0].markdown(f"**{s['last_name']}, {s['first_name']} {s.get('middle_name','')}**  \nLRN: `{s.get('lrn','—')}`")
            cols[1].markdown(f"{s.get('grade_level','—')} — {s.get('section','—')}")
            cols[2].markdown(s.get('gender','—'))
            cols[3].markdown(f"SY {s.get('school_year','—')}")
            cols[4].markdown(f"📞 {s.get('guardian_contact','—')}")
            if is_admin():
                if cols[5].button("✏️", key=f"es_{sid}", help="Edit"):
                    st.session_state.edit_student = sid; st.rerun()
                if cols[6].button("🗑️", key=f"ds_{sid}", help="Delete"):
                    students_col.delete_one({"_id":ObjectId(sid)})
                    grades_col.delete_many({"student_oid":sid})
                    st.success(f"Deleted {s['last_name']}, {s['first_name']} and their grade records.")
                    st.rerun()
            st.divider()

    # ── Inline Edit Form ─────────────────────────────────────────
    if is_admin() and st.session_state.edit_student:
        sid = st.session_state.edit_student
        s   = students_col.find_one({"_id":ObjectId(sid)})
        if s:
            st.markdown("---")
            st.subheader(f"✏️ Editing: {s['last_name']}, {s['first_name']}")
            with st.form("edit_student_form"):
                st.markdown("**Personal Information**")
                c1,c2,c3 = st.columns(3)
                ln  = c1.text_input("Last Name *",  value=s.get("last_name",""))
                fn  = c2.text_input("First Name *", value=s.get("first_name",""))
                mn  = c3.text_input("Middle Name",  value=s.get("middle_name",""))
                c4,c5,c6 = st.columns(3)
                lrn = c4.text_input("LRN",         value=s.get("lrn",""))
                gen = c5.selectbox("Gender *",["Male","Female"], index=0 if s.get("gender","Male")=="Male" else 1)
                suf = c6.text_input("Suffix",      value=s.get("suffix",""), placeholder="Jr., Sr., III")
                c7,c8,c9 = st.columns(3)
                try:    bday_def = datetime.strptime(s.get("birthday","2010-01-01"),"%Y-%m-%d").date()
                except: bday_def = date(2010,1,1)
                bday = c7.date_input("Birthday *", value=bday_def, min_value=date(1990,1,1), max_value=date.today())
                pob  = c8.text_input("Place of Birth",   value=s.get("place_of_birth",""))
                rel_idx = RELIGIONS.index(s.get("religion",RELIGIONS[0])) if s.get("religion") in RELIGIONS else 0
                rel  = c9.selectbox("Religion", RELIGIONS, index=rel_idx)
                mt_idx = MOTHER_TONGUES.index(s.get("mother_tongue",MOTHER_TONGUES[0])) if s.get("mother_tongue") in MOTHER_TONGUES else 0
                mt   = st.selectbox("Mother Tongue", MOTHER_TONGUES, index=mt_idx)
                addr = st.text_area("Complete Address", value=s.get("address",""))

                st.markdown("**Academic Information**")
                a1,a2,a3,a4 = st.columns(4)
                gl_idx = GRADE_LEVELS.index(s.get("grade_level",GRADE_LEVELS[0])) if s.get("grade_level") in GRADE_LEVELS else 0
                grade  = a1.selectbox("Grade Level *", GRADE_LEVELS, index=gl_idx)
                sec    = a2.text_input("Section *", value=s.get("section",""))
                sylist = school_years()
                sy_idx = sylist.index(s.get("school_year",sylist[0])) if s.get("school_year") in sylist else 0
                sy     = a3.selectbox("School Year *", sylist, index=sy_idx)
                st_opts= ["New","Old","Transferee","Returnee"]
                st_idx = st_opts.index(s.get("student_type","Old")) if s.get("student_type") in st_opts else 1
                stype  = a4.selectbox("Student Type", st_opts, index=st_idx)

                st.markdown("**Family / Guardian**")
                b1,b2 = st.columns(2)
                fname  = b1.text_input("Father's Name",       value=s.get("father_name",""))
                focc   = b2.text_input("Father's Occupation", value=s.get("father_occupation",""))
                c1,c2  = st.columns(2)
                mname  = c1.text_input("Mother's Name",       value=s.get("mother_name",""))
                mocc   = c2.text_input("Mother's Occupation", value=s.get("mother_occupation",""))
                d1,d2,d3 = st.columns(3)
                gname  = d1.text_input("Guardian's Name",        value=s.get("guardian_name",""))
                grel   = d2.text_input("Guardian's Relationship",value=s.get("guardian_relationship",""))
                gcon   = d3.text_input("Guardian's Contact",     value=s.get("guardian_contact",""))

                cc1,cc2 = st.columns(2)
                save_s   = cc1.form_submit_button("💾 Save Changes", use_container_width=True)
                cancel_s = cc2.form_submit_button("✖ Cancel",        use_container_width=True)
                if save_s:
                    if not ln or not fn or not sec:
                        st.error("Last name, first name, and section are required.")
                    else:
                        students_col.update_one({"_id":ObjectId(sid)},{"$set":{
                            "last_name":ln.strip(),"first_name":fn.strip(),"middle_name":mn.strip(),
                            "suffix":suf.strip(),"lrn":lrn.strip(),"gender":gen,
                            "birthday":bday.strftime("%Y-%m-%d"),"place_of_birth":pob.strip(),
                            "religion":rel,"mother_tongue":mt,"address":addr.strip(),
                            "grade_level":grade,"section":sec.strip(),"school_year":sy,"student_type":stype,
                            "father_name":fname.strip(),"father_occupation":focc.strip(),
                            "mother_name":mname.strip(),"mother_occupation":mocc.strip(),
                            "guardian_name":gname.strip(),"guardian_relationship":grel.strip(),
                            "guardian_contact":gcon.strip(),
                        }})
                        st.session_state.edit_student = None
                        st.success("✅ Student updated!"); st.rerun()
                if cancel_s:
                    st.session_state.edit_student = None; st.rerun()

    # ── TAB: Profile ─────────────────────────────────────────────
    with T[1]:
        all_s = list(students_col.find().sort("last_name",1))
        if not all_s: st.info("No students yet.")
        else:
            opts = {oid(s): f"{s['last_name']}, {s['first_name']} (LRN: {s.get('lrn','—')})" for s in all_s}
            sel  = st.selectbox("Select Student:", list(opts.keys()), format_func=lambda x: opts[x])
            if sel:
                s = students_col.find_one({"_id":ObjectId(sel)})
                st.markdown("### 👤 Student Profile")
                c1,c2,c3 = st.columns(3)
                with c1:
                    st.markdown(f"**Full Name:** {s.get('last_name')}, {s.get('first_name')} {s.get('middle_name','')} {s.get('suffix','')}")
                    st.markdown(f"**LRN:** `{s.get('lrn','—')}`")
                    st.markdown(f"**Gender:** {s.get('gender','—')}")
                    st.markdown(f"**Birthday:** {s.get('birthday','—')}  *(Age: {calc_age(s.get('birthday',''))})*")
                    st.markdown(f"**Place of Birth:** {s.get('place_of_birth','—')}")
                with c2:
                    st.markdown(f"**Religion:** {s.get('religion','—')}")
                    st.markdown(f"**Mother Tongue:** {s.get('mother_tongue','—')}")
                    st.markdown(f"**Address:** {s.get('address','—')}")
                    st.markdown(f"**Student Type:** {s.get('student_type','—')}")
                with c3:
                    st.markdown(f"**Grade Level:** {s.get('grade_level','—')}")
                    st.markdown(f"**Section:** {s.get('section','—')}")
                    st.markdown(f"**School Year:** {s.get('school_year','—')}")
                    st.markdown(f"**Date Added:** {s.get('date_added','—')}")
                st.markdown("---")
                st.markdown(f"👨 **Father:** {s.get('father_name','—')} · {s.get('father_occupation','—')}  "
                            f"  👩 **Mother:** {s.get('mother_name','—')} · {s.get('mother_occupation','—')}  "
                            f"  🛡️ **Guardian:** {s.get('guardian_name','—')} ({s.get('guardian_relationship','—')}) · 📞 {s.get('guardian_contact','—')}")
                sg = list(grades_col.find({"student_oid":oid(s)}))
                if sg:
                    st.markdown("**📝 Grade Records:**")
                    gdf = pd.DataFrame(sg)[["subject","grade","quarter","submitted_by","date_submitted"]]
                    gdf.columns = ["Subject","Grade","Quarter","Teacher","Date"]
                    st.dataframe(gdf, use_container_width=True)
                else: st.info("No grades submitted yet.")

                if is_admin():
                    if st.button("🎓 Graduate → Move to Alumni", key="grad_btn"):
                        copy = {k:v for k,v in s.items() if k != "_id"}
                        copy.update(graduation_year=str(datetime.now().year),
                                    archived_date=datetime.now().strftime("%Y-%m-%d"),
                                    honors="")
                        alumni_col.insert_one(copy)
                        students_col.delete_one({"_id":s["_id"]})
                        st.success(f"✅ {s['last_name']}, {s['first_name']} moved to Alumni."); st.rerun()

    # ── TAB: Add Student ─────────────────────────────────────────
    if is_admin():
        with T[2]:
            st.subheader("➕ Add New Student")
            with st.form("add_student_form", clear_on_submit=True):
                st.markdown("**Personal Information**")
                c1,c2,c3 = st.columns(3)
                ln  = c1.text_input("Last Name *")
                fn  = c2.text_input("First Name *")
                mn  = c3.text_input("Middle Name")
                c4,c5,c6 = st.columns(3)
                lrn = c4.text_input("LRN (Learner Reference No.)")
                gen = c5.selectbox("Gender *",["Male","Female"])
                suf = c6.text_input("Suffix", placeholder="Jr., Sr., III")
                c7,c8,c9 = st.columns(3)
                bday = c7.date_input("Birthday *", value=date(2010,1,1), min_value=date(1990,1,1), max_value=date.today())
                pob  = c8.text_input("Place of Birth")
                rel  = c9.selectbox("Religion", RELIGIONS)
                mt   = st.selectbox("Mother Tongue", MOTHER_TONGUES)
                addr = st.text_area("Complete Address")

                st.markdown("**Academic Information**")
                a1,a2,a3,a4 = st.columns(4)
                grade = a1.selectbox("Grade Level *", GRADE_LEVELS)
                sec   = a2.text_input("Section *", placeholder="e.g. Rizal")
                sy    = a3.selectbox("School Year *", school_years())
                stype = a4.selectbox("Student Type",["New","Old","Transferee","Returnee"])

                st.markdown("**Family / Guardian**")
                b1,b2 = st.columns(2)
                fname = b1.text_input("Father's Name");  focc = b2.text_input("Father's Occupation")
                c1,c2 = st.columns(2)
                mname = c1.text_input("Mother's Name");  mocc = c2.text_input("Mother's Occupation")
                d1,d2,d3 = st.columns(3)
                gname = d1.text_input("Guardian's Name")
                grel  = d2.text_input("Relationship to Student")
                gcon  = d3.text_input("Guardian's Contact No.")

                if st.form_submit_button("💾 Save Student", use_container_width=True):
                    if not ln or not fn or not sec:
                        st.error("Last name, first name, and section are required.")
                    elif lrn and students_col.find_one({"lrn":lrn.strip()}):
                        st.error(f"LRN **{lrn}** already exists.")
                    else:
                        students_col.insert_one({
                            "last_name":ln.strip(),"first_name":fn.strip(),"middle_name":mn.strip(),
                            "suffix":suf.strip(),"lrn":lrn.strip(),"gender":gen,
                            "birthday":bday.strftime("%Y-%m-%d"),"place_of_birth":pob.strip(),
                            "religion":rel,"mother_tongue":mt,"address":addr.strip(),
                            "grade_level":grade,"section":sec.strip(),"school_year":sy,"student_type":stype,
                            "father_name":fname.strip(),"father_occupation":focc.strip(),
                            "mother_name":mname.strip(),"mother_occupation":mocc.strip(),
                            "guardian_name":gname.strip(),"guardian_relationship":grel.strip(),
                            "guardian_contact":gcon.strip(),
                            "date_added":datetime.now().strftime("%Y-%m-%d"),
                        })
                        st.success(f"✅ {ln}, {fn} added successfully!")


# ═════════════════════════════════════════════════════════════════
#  PAGE 3 — ALUMNI & GRADUATES
# ═════════════════════════════════════════════════════════════════
elif page == "🎓 Alumni & Graduates":
    st.title("🎓 Alumni & Graduates")
    st.markdown("---")

    with st.expander("🔍 Filter Alumni", expanded=True):
        af1,af2,af3 = st.columns(3)
        af_name = af1.text_input("Name or LRN")
        af_year = af2.selectbox("Graduation Year", ["All"]+[str(y) for y in range(datetime.now().year, datetime.now().year-15,-1)])
        af_hon  = af3.text_input("Honors / Awards")

    aq = {}
    if af_name: aq["$or"]=[{"first_name":{"$regex":af_name,"$options":"i"}},{"last_name":{"$regex":af_name,"$options":"i"}}]
    if af_year != "All": aq["graduation_year"] = af_year
    if af_hon:  aq["honors"] = {"$regex":af_hon,"$options":"i"}
    alumni = list(alumni_col.find(aq).sort("last_name",1))

    tabs = ["📋 Alumni List"] + (["➕ Add Alumni"] if is_admin() else [])
    T = st.tabs(tabs)

    with T[0]:
        st.caption(f"Found **{len(alumni)}** alumni record(s)")
        if not alumni: st.info("No alumni records yet. Graduate a student from Student Records, or add manually.")
        for a in alumni:
            aid  = oid(a)
            cols = st.columns([3,2,2,2,1,1] if is_admin() else [3,2,2,2])
            cols[0].markdown(f"**{a.get('last_name')}, {a.get('first_name')} {a.get('middle_name','')}**  \nLRN: `{a.get('lrn','—')}`")
            cols[1].markdown(f"Graduated: **{a.get('graduation_year','—')}**")
            cols[2].markdown(f"SY {a.get('school_year','—')}")
            cols[3].markdown(f"🏅 {a.get('honors','—') or '—'}")
            if is_admin():
                if cols[4].button("✏️",key=f"ea_{aid}"):
                    st.session_state.edit_alumni = aid; st.rerun()
                if cols[5].button("🗑️",key=f"da_{aid}"):
                    alumni_col.delete_one({"_id":ObjectId(aid)})
                    st.success("Alumni record deleted."); st.rerun()
            st.divider()

    if is_admin() and st.session_state.edit_alumni:
        aid = st.session_state.edit_alumni
        a   = alumni_col.find_one({"_id":ObjectId(aid)})
        if a:
            st.markdown("---")
            st.subheader(f"✏️ Edit Alumni: {a.get('last_name')}, {a.get('first_name')}")
            with st.form("edit_alumni_form"):
                c1,c2,c3 = st.columns(3)
                ln  = c1.text_input("Last Name *",    value=a.get("last_name",""))
                fn  = c2.text_input("First Name *",   value=a.get("first_name",""))
                mn  = c3.text_input("Middle Name",    value=a.get("middle_name",""))
                c4,c5 = st.columns(2)
                gy  = c4.text_input("Graduation Year",value=a.get("graduation_year",""))
                hon = c5.text_input("Honors / Awards",value=a.get("honors",""),placeholder="e.g. With Honors, Valedictorian")
                rem = st.text_area("Remarks", value=a.get("remarks",""))
                cc1,cc2 = st.columns(2)
                sa = cc1.form_submit_button("💾 Save", use_container_width=True)
                ca = cc2.form_submit_button("✖ Cancel", use_container_width=True)
                if sa:
                    alumni_col.update_one({"_id":ObjectId(aid)},{"$set":{
                        "last_name":ln.strip(),"first_name":fn.strip(),"middle_name":mn.strip(),
                        "graduation_year":gy.strip(),"honors":hon.strip(),"remarks":rem.strip(),
                    }})
                    st.session_state.edit_alumni = None
                    st.success("✅ Alumni record updated!"); st.rerun()
                if ca:
                    st.session_state.edit_alumni = None; st.rerun()

    if is_admin() and len(T) > 1:
        with T[1]:
            st.subheader("➕ Add Alumni Record Manually")
            with st.form("add_alumni_form", clear_on_submit=True):
                c1,c2,c3 = st.columns(3)
                ln  = c1.text_input("Last Name *")
                fn  = c2.text_input("First Name *")
                mn  = c3.text_input("Middle Name")
                c4,c5,c6 = st.columns(3)
                lrn = c4.text_input("LRN")
                gen = c5.selectbox("Gender",["Male","Female"])
                gy  = c6.text_input("Graduation Year *", placeholder=str(datetime.now().year))
                c7,c8 = st.columns(2)
                sy  = c7.selectbox("School Year", school_years())
                hon = c8.text_input("Honors / Awards", placeholder="e.g. Valedictorian, With Honors")
                rem = st.text_area("Remarks")
                if st.form_submit_button("💾 Save", use_container_width=True):
                    if not ln or not fn or not gy:
                        st.error("Last name, first name, and graduation year are required.")
                    else:
                        alumni_col.insert_one({
                            "last_name":ln.strip(),"first_name":fn.strip(),"middle_name":mn.strip(),
                            "lrn":lrn.strip(),"gender":gen,"graduation_year":gy.strip(),
                            "school_year":sy,"honors":hon.strip(),"remarks":rem.strip(),
                            "date_added":datetime.now().strftime("%Y-%m-%d"),
                        })
                        st.success(f"✅ Alumni {ln}, {fn} added!")


# ═════════════════════════════════════════════════════════════════
#  PAGE 4 — ENROLLMENT / TRANSFER
# ═════════════════════════════════════════════════════════════════
elif page == "📋 Enrollment / Transfer":
    st.title("📋 Enrollment / Transfer Applications")
    st.markdown("---")

    with st.expander("🔍 Filter Applications", expanded=True):
        ef1,ef2,ef3,ef4 = st.columns(4)
        ef_name   = ef1.text_input("Applicant Name")
        ef_type   = ef2.selectbox("Type",   ["All"]+APP_TYPES)
        ef_status = ef3.selectbox("Status", ["All"]+STATUS_OPTS)
        ef_year   = ef4.selectbox("School Year", ["All"]+school_years())

    eq = {}
    if ef_name:            eq["applicant_name"]   = {"$regex":ef_name,"$options":"i"}
    if ef_type   != "All": eq["application_type"] = ef_type
    if ef_status != "All": eq["status"]           = ef_status
    if ef_year   != "All": eq["school_year"]      = ef_year
    enrollments = list(enroll_col.find(eq).sort("date_applied",-1))

    tabs = ["📋 Applications"] + (["➕ New Application"] if is_admin() else [])
    T = st.tabs(tabs)

    with T[0]:
        st.caption(f"Found **{len(enrollments)}** application(s)")
        if not enrollments: st.info("No applications found.")
        STATUS_ICON = {"Pending":"🟡","Approved":"🟢","Enrolled":"🔵","Rejected":"🔴","Transferred Out":"⚫"}
        for e in enrollments:
            eid  = oid(e)
            cols = st.columns([3,2,2,2,2,1,1] if is_admin() else [3,2,2,2,2])
            cols[0].markdown(f"**{e.get('applicant_name','')}**  \n{e.get('application_type','')}")
            cols[1].markdown(f"{e.get('grade_applying','—')} · SY {e.get('school_year','—')}")
            cols[2].markdown(f"{STATUS_ICON.get(e.get('status','Pending'),'🟡')} **{e.get('status','Pending')}**")
            cols[3].markdown(f"📅 {e.get('date_applied','—')}")
            cols[4].markdown(f"🏫 {e.get('previous_school','') or '—'}")
            if is_admin():
                if cols[5].button("✏️",key=f"ee_{eid}"):
                    st.session_state.edit_enrollment = eid; st.rerun()
                if cols[6].button("🗑️",key=f"de_{eid}"):
                    enroll_col.delete_one({"_id":ObjectId(eid)})
                    st.success("Application deleted."); st.rerun()
            st.divider()

    if is_admin() and st.session_state.edit_enrollment:
        eid = st.session_state.edit_enrollment
        e   = enroll_col.find_one({"_id":ObjectId(eid)})
        if e:
            st.markdown("---")
            st.subheader(f"✏️ Update Application: {e.get('applicant_name')}")
            with st.form("edit_enroll_form"):
                c1,c2 = st.columns(2)
                ns = c1.selectbox("Status *", STATUS_OPTS, index=STATUS_OPTS.index(e.get("status","Pending")) if e.get("status") in STATUS_OPTS else 0)
                ng = c2.selectbox("Grade Applying", GRADE_LEVELS, index=GRADE_LEVELS.index(e.get("grade_applying",GRADE_LEVELS[0])) if e.get("grade_applying") in GRADE_LEVELS else 0)
                nr = st.text_area("Admin Notes", value=e.get("notes",""))
                cc1,cc2 = st.columns(2)
                se = cc1.form_submit_button("💾 Save", use_container_width=True)
                ce = cc2.form_submit_button("✖ Cancel", use_container_width=True)
                if se:
                    enroll_col.update_one({"_id":ObjectId(eid)},{"$set":{
                        "status":ns,"grade_applying":ng,"notes":nr.strip(),
                        "last_updated":datetime.now().strftime("%Y-%m-%d"),
                    }})
                    st.session_state.edit_enrollment = None
                    st.success("✅ Application updated!"); st.rerun()
                if ce:
                    st.session_state.edit_enrollment = None; st.rerun()

    if is_admin() and len(T) > 1:
        with T[1]:
            st.subheader("➕ New Application")
            with st.form("add_enroll_form", clear_on_submit=True):
                c1,c2,c3 = st.columns(3)
                aname = c1.text_input("Applicant Full Name *")
                atype = c2.selectbox("Application Type *", APP_TYPES)
                agr   = c3.selectbox("Grade Applying For *", GRADE_LEVELS)
                c4,c5,c6 = st.columns(3)
                sy    = c4.selectbox("School Year *", school_years())
                prev  = c5.text_input("Previous School", placeholder="For transfers")
                cont  = c6.text_input("Contact Number")
                st.markdown("**Documents Checklist**")
                dc1,dc2,dc3 = st.columns(3)
                d1 = dc1.checkbox("Birth Certificate (PSA)")
                d2 = dc2.checkbox("Form 137 / SF10")
                d3 = dc3.checkbox("Good Moral Certificate")
                d4 = dc1.checkbox("Report Card / Form 138")
                d5 = dc2.checkbox("2x2 ID Photo")
                notes = st.text_area("Notes / Remarks")
                if st.form_submit_button("💾 Submit Application", use_container_width=True):
                    if not aname: st.error("Applicant name is required.")
                    else:
                        enroll_col.insert_one({
                            "applicant_name":aname.strip(),"application_type":atype,
                            "grade_applying":agr,"school_year":sy,"previous_school":prev.strip(),
                            "contact":cont.strip(),"status":"Pending",
                            "documents":{"birth_cert":d1,"form137":d2,"good_moral":d3,"report_card":d4,"photo":d5},
                            "notes":notes.strip(),"date_applied":datetime.now().strftime("%Y-%m-%d"),
                        })
                        st.success(f"✅ Application for **{aname}** submitted!")


# ═════════════════════════════════════════════════════════════════
#  PAGE 5 — GRADE SUBMISSION
# ═════════════════════════════════════════════════════════════════
elif page == "📝 Grade Submission":
    st.title("📝 Grade Submission")
    st.markdown("---")

    all_students = list(students_col.find().sort("last_name",1))
    all_grades   = list(grades_col.find().sort("date_submitted",-1))

    tabs = (["➕ Submit Grade"] if is_admin() else []) + ["📋 View Grades"]
    T    = st.tabs(tabs)
    submit_tab = T[0] if is_admin() else None
    view_tab   = T[1] if is_admin() else T[0]

    if is_admin() and submit_tab:
        with submit_tab:
            if not all_students: st.warning("No students found. Add students first.")
            else:
                with st.form("submit_grade_form", clear_on_submit=True):
                    smap = {oid(s): f"{s['last_name']}, {s['first_name']} (LRN: {s.get('lrn','—')})" for s in all_students}
                    c1,c2 = st.columns(2)
                    sel_s   = c1.selectbox("Student *", list(smap.keys()), format_func=lambda x: smap[x])
                    subject = c2.selectbox("Subject *", SUBJECTS)
                    c3,c4,c5 = st.columns(3)
                    quarter  = c3.selectbox("Quarter *", QUARTERS)
                    grade_v  = c4.number_input("Grade (60–100) *", 60, 100, 85, 1)
                    teacher  = c5.text_input("Teacher Name *")
                    remarks  = st.text_area("Remarks (optional)")
                    if st.form_submit_button("💾 Submit Grade", use_container_width=True):
                        if not teacher: st.error("Teacher name is required.")
                        elif grades_col.find_one({"student_oid":sel_s,"subject":subject,"quarter":quarter}):
                            st.warning("Grade already exists for this student/subject/quarter. Edit it in View Grades.")
                        else:
                            s = students_col.find_one({"_id":ObjectId(sel_s)})
                            grades_col.insert_one({
                                "student_oid":sel_s,
                                "student_name":f"{s['last_name']}, {s['first_name']}",
                                "subject":subject,"quarter":quarter,"grade":grade_v,
                                "submitted_by":teacher.strip(),"remarks":remarks.strip(),
                                "date_submitted":datetime.now().strftime("%Y-%m-%d"),
                            })
                            st.success(f"✅ Grade submitted — {smap[sel_s]} · {subject} {quarter}: **{grade_v}**")

    with view_tab:
        gf1,gf2,gf3,gf4 = st.columns(4)
        gf_name    = gf1.text_input("Search student")
        gf_subject = gf2.selectbox("Subject", ["All"]+SUBJECTS)
        gf_quarter = gf3.selectbox("Quarter", ["All"]+QUARTERS)
        snames     = sorted(set(g.get("student_name","") for g in all_grades))
        gf_student = gf4.selectbox("Student", ["All"]+snames)

        filtered = all_grades
        if gf_name:             filtered = [g for g in filtered if gf_name.lower() in g.get("student_name","").lower()]
        if gf_subject != "All": filtered = [g for g in filtered if g["subject"] == gf_subject]
        if gf_quarter != "All": filtered = [g for g in filtered if g["quarter"] == gf_quarter]
        if gf_student != "All": filtered = [g for g in filtered if g["student_name"] == gf_student]

        # Edit grade form
        if is_admin() and st.session_state.edit_grade:
            gid = st.session_state.edit_grade
            g   = grades_col.find_one({"_id":ObjectId(gid)})
            if g:
                st.subheader(f"✏️ Edit: {g['student_name']} — {g['subject']} {g['quarter']}")
                with st.form("edit_grade_form"):
                    ec1,ec2,ec3 = st.columns(3)
                    ng = ec1.number_input("Grade", 60, 100, int(g["grade"]), 1)
                    nq = ec2.selectbox("Quarter", QUARTERS, index=QUARTERS.index(g["quarter"]))
                    nt = ec3.text_input("Teacher", value=g["submitted_by"])
                    nr = st.text_input("Remarks", value=g.get("remarks",""))
                    gc1,gc2 = st.columns(2)
                    sg = gc1.form_submit_button("💾 Save", use_container_width=True)
                    cg = gc2.form_submit_button("✖ Cancel", use_container_width=True)
                    if sg:
                        grades_col.update_one({"_id":ObjectId(gid)},{"$set":{
                            "grade":ng,"quarter":nq,"submitted_by":nt.strip(),"remarks":nr.strip(),
                            "date_submitted":datetime.now().strftime("%Y-%m-%d"),
                        }})
                        st.session_state.edit_grade = None
                        st.success("✅ Grade updated!"); st.rerun()
                    if cg:
                        st.session_state.edit_grade = None; st.rerun()
                st.markdown("---")

        st.caption(f"Showing **{len(filtered)}** record(s)")
        if not filtered: st.info("No grade records match the filter.")
        for g in filtered:
            gid  = oid(g)
            cols = st.columns([3,2,1,1,2,1,1] if is_admin() else [3,2,1,1,2])
            cols[0].markdown(f"**{g.get('student_name','—')}**")
            cols[1].markdown(g.get("subject","—"))
            cols[2].markdown(f"**{g.get('grade','—')}**")
            cols[3].markdown(g.get("quarter","—"))
            cols[4].markdown(f"👤 {g.get('submitted_by','—')}  \n📅 {g.get('date_submitted','—')}")
            if is_admin():
                if cols[5].button("✏️",key=f"eg_{gid}"):
                    st.session_state.edit_grade = gid; st.rerun()
                if cols[6].button("🗑️",key=f"dg_{gid}"):
                    grades_col.delete_one({"_id":ObjectId(gid)})
                    st.success("Grade deleted."); st.rerun()
            st.divider()


# ═════════════════════════════════════════════════════════════════
#  PAGE 6 — OFFICE INVENTORY
# ═════════════════════════════════════════════════════════════════
elif page == "📦 Office Inventory":
    st.title("📦 Office Inventory")
    st.markdown("---")

    inventory = list(inventory_col.find().sort("item_name",1))
    tabs = ["📋 View Inventory"] + (["➕ Add / Restock","➖ Deduct Stock"] if is_admin() else [])
    T = st.tabs(tabs)

    with T[0]:
        if1,if2 = st.columns(2)
        if_name = if1.text_input("🔍 Search item")
        if_cat  = if2.selectbox("Category", ["All"]+CATEGORIES_INV)
        fi = [i for i in inventory if (not if_name or if_name.lower() in i["item_name"].lower())
              and (if_cat == "All" or i["category"] == if_cat)]
        st.caption(f"Showing **{len(fi)}** item(s)")

        # Edit form
        if is_admin() and st.session_state.edit_inventory:
            iid  = st.session_state.edit_inventory
            item = inventory_col.find_one({"_id":ObjectId(iid)})
            if item:
                st.subheader(f"✏️ Edit: {item['item_name']}")
                with st.form("edit_inv_form"):
                    ic1,ic2 = st.columns(2)
                    nin  = ic1.text_input("Item Name *", value=item["item_name"])
                    ncat = ic2.selectbox("Category *", CATEGORIES_INV,
                        index=CATEGORIES_INV.index(item["category"]) if item["category"] in CATEGORIES_INV else 0)
                    ic3,ic4 = st.columns(2)
                    nqty  = ic3.number_input("Quantity *", 0, value=item["quantity"], step=1)
                    nunit = ic4.selectbox("Unit", UNITS,
                        index=UNITS.index(item["unit"]) if item["unit"] in UNITS else 0)
                    nnotes = st.text_input("Notes", value=item.get("notes",""))
                    icc1,icc2 = st.columns(2)
                    si = icc1.form_submit_button("💾 Save", use_container_width=True)
                    ci = icc2.form_submit_button("✖ Cancel", use_container_width=True)
                    if si:
                        inventory_col.update_one({"_id":ObjectId(iid)},{"$set":{
                            "item_name":nin.strip(),"category":ncat,"quantity":nqty,
                            "unit":nunit,"notes":nnotes.strip(),
                            "date_updated":datetime.now().strftime("%Y-%m-%d"),
                        }})
                        st.session_state.edit_inventory = None
                        st.success("✅ Item updated!"); st.rerun()
                    if ci:
                        st.session_state.edit_inventory = None; st.rerun()
                st.markdown("---")

        if not fi: st.info("No items found.")
        for item in fi:
            iid  = oid(item)
            low  = item.get("quantity",0) <= 5
            cols = st.columns([3,2,1,2,1,1] if is_admin() else [3,2,1,2])
            cols[0].markdown(f"**{item['item_name']}**  \n_{item.get('notes','')}_")
            cols[1].markdown(f"📂 {item['category']}")
            cols[2].markdown(f"{'⚠️ ' if low else ''}**{item['quantity']}** {item['unit']}")
            cols[3].markdown(f"📅 {item.get('date_added','—')}")
            if is_admin():
                if cols[4].button("✏️",key=f"ei_{iid}"):
                    st.session_state.edit_inventory = iid; st.rerun()
                if cols[5].button("🗑️",key=f"di_{iid}"):
                    inventory_col.delete_one({"_id":ObjectId(iid)})
                    st.success(f"**{item['item_name']}** deleted."); st.rerun()
            st.divider()

        if inventory:
            st.subheader("📊 Stock by Category")
            cdf = pd.DataFrame(inventory).groupby("category")["quantity"].sum().reset_index()
            cdf.columns = ["Category","Total"]
            st.bar_chart(cdf.set_index("Category")["Total"])

    if is_admin() and len(T) > 1:
        with T[1]:
            with st.form("add_inv_form", clear_on_submit=True):
                c1,c2 = st.columns(2)
                iname = c1.text_input("Item Name *")
                icat  = c2.selectbox("Category *", CATEGORIES_INV)
                c3,c4 = st.columns(2)
                iqty  = c3.number_input("Quantity *", 0, value=1, step=1)
                iunit = c4.selectbox("Unit", UNITS)
                inotes = st.text_input("Notes (optional)")
                if st.form_submit_button("💾 Save Item", use_container_width=True):
                    if not iname: st.error("Item name is required.")
                    else:
                        ex = inventory_col.find_one({"item_name":{"$regex":f"^{iname}$","$options":"i"}})
                        if ex:
                            inventory_col.update_one({"_id":ex["_id"]},{"$inc":{"quantity":iqty}})
                            st.success(f"✅ Restocked **{iname}**. New qty: {ex['quantity']+iqty} {iunit}")
                        else:
                            inventory_col.insert_one({
                                "item_name":iname.strip(),"category":icat,"quantity":iqty,
                                "unit":iunit,"notes":inotes.strip(),
                                "date_added":datetime.now().strftime("%Y-%m-%d"),
                            })
                            st.success(f"✅ **{iname}** added ({iqty} {iunit}).")

    if is_admin() and len(T) > 2:
        with T[2]:
            if not inventory: st.info("No items in inventory yet.")
            else:
                with st.form("deduct_form"):
                    c1,c2 = st.columns(2)
                    sel_i = c1.selectbox("Select Item", [i["item_name"] for i in inventory])
                    dqty  = c2.number_input("Quantity to Deduct", 1, value=1, step=1)
                    rsn   = st.text_input("Reason (optional)", placeholder="e.g. Used for enrollment forms")
                    if st.form_submit_button("➖ Deduct", use_container_width=True):
                        item = inventory_col.find_one({"item_name":sel_i})
                        if item and dqty > item["quantity"]:
                            st.error(f"Cannot deduct {dqty} — only {item['quantity']} in stock.")
                        elif item:
                            inventory_col.update_one({"_id":item["_id"]},{"$inc":{"quantity":-dqty}})
                            st.success(f"✅ Deducted {dqty} from **{sel_i}**. Remaining: **{item['quantity']-dqty}**")