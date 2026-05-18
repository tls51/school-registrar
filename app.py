import streamlit as st           # Streamlit builds our web UI
import pandas as pd           # Pandas helps us work with tables of data
import json                   # JSON is how we save/load data from files
import os                     # OS lets us check if files exist
from datetime import datetime # For timestamps (e.g. when a grade was added)

# ─────────────────────────────────────────────
#  FILE PATHS — where we store our data
# ─────────────────────────────────────────────
STUDENTS_FILE  = "students.json"
GRADES_FILE    = "grades.json"
INVENTORY_FILE = "inventory.json"


# ─────────────────────────────────────────────
#  HELPER FUNCTIONS — load and save data
# ─────────────────────────────────────────────

def load_data(file_path):
    """Read data from a JSON file. Returns an empty list if file doesn't exist yet."""
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return []

def save_data(file_path, data):
    """Write data to a JSON file so it's saved between sessions."""
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


# ─────────────────────────────────────────────
#  PAGE CONFIG — sets the browser tab title & layout
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="School Registrar System",
    page_icon="🏫",
    layout="wide"
)

# ─────────────────────────────────────────────
#  SIDEBAR NAVIGATION & SECURE LOGIN
# ─────────────────────────────────────────────

st.sidebar.title("🏫 Registrar System")
st.sidebar.markdown("---")

# Initialize authentication session state variables if they don't exist
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False

st.sidebar.subheader("🔐 Access Control")

# Render UI based on whether the admin is logged in
if st.session_state["is_admin"]:
    st.sidebar.success("🔑 Status: **Logged in as Admin**")
    if st.sidebar.button("🚪 Log Out", use_container_width=True, type="primary"):
        st.session_state["is_admin"] = False
        st.success("Logged out successfully!")
        st.rerun()
else:
    st.sidebar.info("👀 Status: **User (View Only)**")
    with st.sidebar.expander("🔑 Admin Authorization"):
        # Set your desired password here
        ADMIN_PASSWORD = "admin123" 
        
        input_password = st.text_input("Enter Admin Password", type="password")
        if st.button("🔓 Login", use_container_width=True):
            if input_password == ADMIN_PASSWORD:
                st.session_state["is_admin"] = True
                st.sidebar.success("Access Granted!")
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")

# Set flags based on persistent session state
is_admin = st.session_state["is_admin"]
user_role = "Admin" if is_admin else "User (View Only)"

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate to:",
    ["🏠 Dashboard", "👤 Student Records", "📝 Grade Submission", "📦 Office Inventory"]
)

st.sidebar.markdown("---")
st.sidebar.caption("School Registrar System v1.2")


# ═════════════════════════════════════════════
#  PAGE 1 — DASHBOARD
# ═════════════════════════════════════════════

if page == "🏠 Dashboard":
    st.title("🏠 Dashboard")
    st.markdown("Welcome to the **School Registrar System**. Use the sidebar to navigate.")
    st.markdown(f"Current Access Level: **{user_role}**")
    st.markdown("---")

    # Load all data to show summary counts
    students  = load_data(STUDENTS_FILE)
    grades    = load_data(GRADES_FILE)
    inventory = load_data(INVENTORY_FILE)

    # Show summary cards side by side
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="👤 Total Students", value=len(students))

    with col2:
        st.metric(label="📝 Grade Records", value=len(grades))

    with col3:
        total_items = sum(item.get("quantity", 0) for item in inventory)
        st.metric(label="📦 Inventory Items", value=total_items)

    st.markdown("---")

    # Show a quick preview of recently added students
    if students:
        st.subheader("📋 Recently Added Students")
        recent = students[-5:][::-1]  # last 5, newest first
        df = pd.DataFrame(recent)[["student_id", "name", "grade_level", "section"]]
        df.columns = ["Student ID", "Name", "Grade Level", "Section"]
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No students yet. Admin must log in to add records!")

    if inventory:
        st.subheader("📦 Low Stock Alerts")
        low_stock = [i for i in inventory if i.get("quantity", 0) <= 5]
        if low_stock:
            for item in low_stock:
                st.warning(f"⚠️  **{item['item_name']}** — only {item['quantity']} left!")
        else:
            st.success("✅ All items are sufficiently stocked.")


# ═════════════════════════════════════════════
#  PAGE 2 — STUDENT RECORDS & PROFILES
# ═════════════════════════════════════════════

elif page == "👤 Student Records":
    st.title("👤 Student Records & Profiles")
    st.markdown("Add, view, and manage student information.")
    st.markdown("---")

    students = load_data(STUDENTS_FILE)

    # ── Tabs: one for viewing, one for adding ──
    tab1, tab2 = st.tabs(["📋 View All Students", "➕ Add New Student"])

    # ── TAB 1: View students ──
    with tab1:
        if not students:
            st.info("No student records yet. Admin must use the **Add New Student** tab to get started.")
        else:
            # Search bar
            search = st.text_input("🔍 Search by name or Student ID")

            filtered = students
            if search:
                search_lower = search.lower()
                filtered = [
                    s for s in students
                    if search_lower in s["name"].lower()
                    or search_lower in s["student_id"].lower()
                ]

            if filtered:
                df = pd.DataFrame(filtered)
                st.dataframe(df[[
                    "student_id", "name", "grade_level",
                    "section", "contact_number", "date_added"
                ]].rename(columns={
                    "student_id": "ID",
                    "name": "Full Name",
                    "grade_level": "Grade Level",
                    "section": "Section",
                    "contact_number": "Contact",
                    "date_added": "Date Added"
                }), use_container_width=True)
                st.caption(f"Showing {len(filtered)} of {len(students)} student(s)")
            else:
                st.warning("No students match your search.")

            # View individual student profile + grades
            st.markdown("---")
            st.subheader("🔎 View Student Profile")

            student_names = {s["student_id"]: s["name"] for s in students}
            selected_id = st.selectbox(
                "Select a student to view profile:",
                options=list(student_names.keys()),
                format_func=lambda x: f"{x} — {student_names[x]}"
            )

            if selected_id:
                student = next(s for s in students if s["student_id"] == selected_id)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Name:** {student['name']}")
                    st.markdown(f"**Student ID:** {student['student_id']}")
                    st.markdown(f"**Grade Level:** {student['grade_level']}")
                with col2:
                    st.markdown(f"**Section:** {student['section']}")
                    st.markdown(f"**Contact:** {student['contact_number']}")
                    st.markdown(f"**Date Added:** {student['date_added']}")

                # 🛠️ ADMIN TOOLS: EDIT OR DELETE STUDENT
                if is_admin:
                    with st.expander("🛠️ Admin Tools: Edit / Delete This Student"):
                        st.markdown("### Update Student Records")
                        edit_name = st.text_input("Modify Full Name", value=student['name'])
                        edit_grade = st.selectbox("Modify Grade Level", 
                                                ["Grade 7", "Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12"],
                                                index=["Grade 7", "Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12"].index(student['grade_level']))
                        edit_section = st.text_input("Modify Section", value=student['section'])
                        edit_contact = st.text_input("Modify Contact Number", value=student['contact_number'])
                        
                        col_edit, col_del = st.columns(2)
                        with col_edit:
                            if st.button("✏️ Save Changes", use_container_width=True):
                                student['name'] = edit_name.strip()
                                student['grade_level'] = edit_grade
                                student['section'] = edit_section.strip()
                                student['contact_number'] = edit_contact.strip()
                                save_data(STUDENTS_FILE, students)
                                st.success("Student records updated successfully!")
                                st.rerun()
                                
                        with col_del:
                            if st.button("🗑️ Delete Student Record", use_container_width=True, type="primary"):
                                # Remove student from list
                                students = [s for s in students if s["student_id"] != selected_id]
                                save_data(STUDENTS_FILE, students)
                                # Cascading deletion: Clean up student grades as well
                                all_grades = load_data(GRADES_FILE)
                                filtered_grades = [g for g in all_grades if g["student_id"] != selected_id]
                                save_data(GRADES_FILE, filtered_grades)
                                st.success("Student record and related grades deleted successfully!")
                                st.rerun()

                # Show that student's grades
                st.markdown("---")
                all_grades = load_data(GRADES_FILE)
                student_grades = [g for g in all_grades if g["student_id"] == selected_id]
                if student_grades:
                    st.markdown("**📝 Grade Records:**")
                    gdf = pd.DataFrame(student_grades)[["subject", "grade", "quarter", "submitted_by", "date_submitted"]]
                    gdf.columns = ["Subject", "Grade", "Quarter", "Submitted By", "Date"]
                    st.dataframe(gdf, use_container_width=True)
                else:
                    st.info("No grades submitted for this student yet.")

    # ── TAB 2: Add a student ──
    with tab2:
        if not is_admin:
            st.warning("🔒 Access Denied: You must complete **Admin Authorization** in the sidebar to register new students.")
        else:
            st.subheader("➕ Add New Student")

            with st.form("add_student_form"):
                col1, col2 = st.columns(2)

                with col1:
                    student_id     = st.text_input("Student ID *", placeholder="e.g. 2024-0001")
                    full_name      = st.text_input("Full Name *",   placeholder="e.g. Juan Dela Cruz")
                    grade_level    = st.selectbox("Grade Level *",
                                        ["Grade 7", "Grade 8", "Grade 9", "Grade 10",
                                         "Grade 11", "Grade 12"])

                with col2:
                    section        = st.text_input("Section *",         placeholder="e.g. Rizal")
                    contact_number = st.text_input("Contact Number",    placeholder="e.g. 09XX-XXX-XXXX")

                submitted = st.form_submit_button("💾 Save Student", use_container_width=True)

                if submitted:
                    if not student_id or not full_name or not section:
                        st.error("Please fill in all required fields (marked with *).")
                    elif any(s["student_id"] == student_id for s in students):
                        st.error(f"Student ID **{student_id}** already exists. Use a unique ID.")
                    else:
                        new_student = {
                            "student_id":     student_id.strip(),
                            "name":           full_name.strip(),
                            "grade_level":    grade_level,
                            "section":        section.strip(),
                            "contact_number": contact_number.strip(),
                            "date_added":     datetime.now().strftime("%Y-%m-%d")
                        }
                        students.append(new_student)   
                        save_data(STUDENTS_FILE, students)  
                        st.success(f"✅ Student **{full_name}** added successfully!")
                        st.rerun()


# ═════════════════════════════════════════════
#  PAGE 3 — TEACHER GRADE SUBMISSION
# ═════════════════════════════════════════════

elif page == "📝 Grade Submission":
    st.title("📝 Grade Submission")
    st.markdown("Submit or view student grades by subject and quarter.")
    st.markdown("---")

    students = load_data(STUDENTS_FILE)
    grades   = load_data(GRADES_FILE)

    tab1, tab2, tab3 = st.tabs(["➕ Submit Grades", "📋 View All Grades", "📊 Grade Summary"])

    # ── TAB 1: Submit grades ──
    with tab1:
        if not is_admin:
            st.warning("🔒 Access Denied: You must complete **Admin Authorization** in the sidebar to submit grades.")
        elif not students:
            st.warning("No students found. Please add students in the **Student Records** section first.")
        else:
            st.subheader("➕ Submit a Grade")

            with st.form("submit_grade_form"):
                col1, col2 = st.columns(2)
                student_map = {s["student_id"]: s["name"] for s in students}

                with col1:
                    selected_student = st.selectbox(
                        "Select Student *",
                        options=list(student_map.keys()),
                        format_func=lambda x: f"{x} — {student_map[x]}"
                    )
                    subject = st.selectbox("Subject *", [
                        "Filipino", "English", "Mathematics", "Science",
                        "Araling Panlipunan", "MAPEH", "TLE", "Values Education",
                        "Computer Science", "Other"
                    ])

                with col2:
                    quarter = st.selectbox("Quarter *", ["Q1", "Q2", "Q3", "Q4"])
                    grade   = st.number_input(
                        "Grade (60–100) *",
                        min_value=60, max_value=100, value=85, step=1
                    )
                    teacher_name = st.text_input("Submitted by (Teacher Name) *",
                                                 placeholder="e.g. Ma. Santos")

                remarks = st.text_area("Remarks (optional)", placeholder="e.g. Needs improvement in fractions")
                submitted = st.form_submit_button("💾 Submit Grade", use_container_width=True)

                if submitted:
                    if not teacher_name:
                        st.error("Please enter the teacher's name.")
                    else:
                        duplicate = any(
                            g["student_id"] == selected_student
                            and g["subject"] == subject
                            and g["quarter"] == quarter
                            for g in grades
                        )
                        if duplicate:
                            st.warning(
                                f"A grade for **{subject}** in **{quarter}** already exists for this student. "
                                "Please delete or update the existing entry down below."
                            )
                        else:
                            new_grade = {
                                "student_id":     selected_student,
                                "student_name":   student_map[selected_student],
                                "subject":        subject,
                                "quarter":        quarter,
                                "grade":          grade,
                                "submitted_by":   teacher_name.strip(),
                                "remarks":        remarks.strip(),
                                "date_submitted": datetime.now().strftime("%Y-%m-%d")
                            }
                            grades.append(new_grade)
                            save_data(GRADES_FILE, grades)
                            st.success(f"✅ Grade submitted for **{student_map[selected_student]}**!")
                            st.rerun()

    # ── TAB 2: View all grades ──
    with tab2:
        if not grades:
            st.info("No grades submitted yet.")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                filter_quarter = st.selectbox("Filter by Quarter", ["All", "Q1", "Q2", "Q3", "Q4"])
            with col2:
                filter_subject = st.selectbox("Filter by Subject", ["All"] + sorted(set(g["subject"] for g in grades)))
            with col3:
                filter_name = st.text_input("Search by student name")

            filtered = grades
            if filter_quarter != "All":
                filtered = [g for g in filtered if g["quarter"] == filter_quarter]
            if filter_subject != "All":
                filtered = [g for g in filtered if g["subject"] == filter_subject]
            if filter_name:
                filtered = [g for g in filtered if filter_name.lower() in g["student_name"].lower()]

            if filtered:
                df = pd.DataFrame(filtered)[[
                    "student_id", "student_name", "subject",
                    "quarter", "grade", "submitted_by", "date_submitted"
                ]]
                df.columns = ["ID", "Student", "Subject", "Quarter", "Grade", "Teacher", "Date"]
                st.dataframe(df, use_container_width=True)
                st.caption(f"Showing {len(filtered)} record(s)")
                
                # 🛠️ ADMIN TOOLS: EDIT / DELETE SPECIFIC GRADE RECORDS
                if is_admin:
                    st.markdown("---")
                    st.subheader("🛠️ Admin Actions: Modify / Drop Grade Record")
                    
                    grade_options = {
                        i: f"{g['student_name']} ({g['student_id']}) — {g['subject']} [{g['quarter']}]"
                        for i, g in enumerate(grades)
                    }
                    
                    selected_grade_idx = st.selectbox(
                        "Choose a specific grade record to modify:",
                        options=list(grade_options.keys()),
                        format_func=lambda x: grade_options[x]
                    )
                    
                    if selected_grade_idx is not None:
                        target_record = grades[selected_grade_idx]
                        
                        col_g1, col_g2 = st.columns(2)
                        with col_g1:
                            new_g_val = st.number_input("Change Grade Evaluation", min_value=60, max_value=100, value=int(target_record["grade"]))
                        with col_g2:
                            new_g_remarks = st.text_area("Update Remarks", value=target_record.get("remarks", ""))
                            
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("✏️ Save Grade Changes", use_container_width=True):
                                grades[selected_grade_idx]["grade"] = new_g_val
                                grades[selected_grade_idx]["remarks"] = new_g_remarks
                                grades[selected_grade_idx]["date_submitted"] = datetime.now().strftime("%Y-%m-%d")
                                save_data(GRADES_FILE, grades)
                                st.success("Grade updated successfully!")
                                st.rerun()
                        with col_btn2:
                            if st.button("🗑️ Delete Grade Entry", use_container_width=True, type="primary"):
                                grades.pop(selected_grade_idx)
                                save_data(GRADES_FILE, grades)
                                st.success("Grade metrics wiped from file database!")
                                st.rerun()
            else:
                st.warning("No records match your filters.")

    # ── TAB 3: Grade summary per student ──
    with tab3:
        if not grades:
            st.info("No grades to summarize yet.")
        elif not students:
            st.info("No students found.")
        else:
            st.subheader("📊 Student Grade Average")
            student_map = {s["student_id"]: s["name"] for s in students}
            selected_id = st.selectbox(
                "Select Student Profile Summary",
                options=list(student_map.keys()),
                format_func=lambda x: f"{x} — {student_map[x]}"
            )

            student_grades = [g for g in grades if g["student_id"] == selected_id]
            if student_grades:
                df = pd.DataFrame(student_grades)

                summary = df.groupby("subject")["grade"].mean().reset_index()
                summary.columns = ["Subject", "Average Grade"]
                summary["Average Grade"] = summary["Average Grade"].round(2)

                overall_avg = df["grade"].mean()
                st.metric("Overall Average", f"{overall_avg:.2f}")

                col1, col2 = st.columns(2)
                with col1:
                    st.dataframe(summary, use_container_width=True)
                with col2:
                    st.bar_chart(summary.set_index("Subject")["Average Grade"])
            else:
                st.info("No grades found for this student.")


# ═════════════════════════════════════════════
#  PAGE 4 — OFFICE INVENTORY
# ═════════════════════════════════════════════

elif page == "📦 Office Inventory":
    st.title("📦 Office Inventory")
    st.markdown("Track office supplies and equipment for the registrar's office.")
    st.markdown("---")

    inventory = load_data(INVENTORY_FILE)

    tab1, tab2 = st.tabs(["📋 View Inventory", "➕ Add / Update Item"])

    # ── TAB 1: View inventory ──
    with tab1:
        if not inventory:
            st.info("No inventory items yet. Admin must use the **Add / Update Item** tab to add supplies.")
        else:
            search = st.text_input("🔍 Search item")

            filtered = inventory
            if search:
                filtered = [i for i in inventory if search.lower() in i["item_name"].lower()]

            if filtered:
                df = pd.DataFrame(filtered)[[
                    "item_name", "category", "quantity", "unit", "date_added"
                ]].rename(columns={
                    "item_name": "Item",
                    "category":  "Category",
                    "quantity":  "Quantity",
                    "unit":      "Unit",
                    "date_added": "Date Added"
                })

                def highlight_low(row):
                    if row["Quantity"] <= 5:
                        return ["background-color: #fff3cd"] * len(row)
                    return [""] * len(row)

                st.dataframe(df.style.apply(highlight_low, axis=1), use_container_width=True)
                st.caption("⚠️ Yellow rows indicate low stock (5 or fewer).")
            else:
                st.warning("No items found matching criteria.")

            # Summary by category
            st.markdown("---")
            st.subheader("📊 Stock by Category")
            cat_summary = pd.DataFrame(inventory).groupby("category")["quantity"].sum().reset_index()
            cat_summary.columns = ["Category", "Total Quantity"]
            st.bar_chart(cat_summary.set_index("Category")["Total Quantity"])

    # ── TAB 2: Add or update item ──
    with tab2:
        if not is_admin:
            st.warning("🔒 Access Denied: You must complete **Admin Authorization** in the sidebar to modify inventory.")
        else:
            st.subheader("➕ Add New Item or Update Stock")

            with st.form("inventory_form"):
                col1, col2 = st.columns(2)

                with col1:
                    item_name = st.text_input("Item Name *", placeholder="e.g. Bond Paper")
                    category  = st.selectbox("Category *", [
                        "Paper & Forms", "Writing Supplies", "Filing & Storage",
                        "Ink & Toner", "Office Equipment", "Cleaning Supplies", "Other"
                    ])

                with col2:
                    quantity = st.number_input("Quantity *", min_value=0, value=1, step=1)
                    unit     = st.selectbox("Unit", ["pieces", "packs", "boxes", "reams", "bottles", "sets"])

                notes = st.text_input("Notes (optional)", placeholder="e.g. Short bond, 500 sheets per ream")
                submitted = st.form_submit_button("💾 Save Item", use_container_width=True)

                if submitted:
                    if not item_name:
                        st.error("Please enter an item name.")
                    else:
                        existing = next(
                            (i for i in inventory if i["item_name"].lower() == item_name.lower()),
                            None
                        )
                        if existing:
                            existing["quantity"] += quantity
                            existing["date_added"] = datetime.now().strftime("%Y-%m-%d")
                            save_data(INVENTORY_FILE, inventory)
                            st.success(f"✅ Quantity updated to **{existing['quantity']} {unit}**.")
                            st.rerun()
                        else:
                            new_item = {
                                "item_name":  item_name.strip(),
                                "category":   category,
                                "quantity":   quantity,
                                "unit":       unit,
                                "notes":      notes.strip(),
                                "date_added": datetime.now().strftime("%Y-%m-%d")
                            }
                            inventory.append(new_item)
                            save_data(INVENTORY_FILE, inventory)
                            st.success(f"✅ **{item_name}** added to inventory.")
                            st.rerun()

            # ── Remove / deduct stock ──
            if inventory:
                st.markdown("---")
                st.subheader("➖ Deduct Stock (Item Used)")

                with st.form("deduct_form"):
                    item_names = [i["item_name"] for i in inventory]
                    selected_item = st.selectbox("Select Item to Deduct From", item_names)
                    deduct_qty    = st.number_input("Quantity to Deduct", min_value=1, value=1, step=1)

                    deduct_btn = st.form_submit_button("➖ Deduct Stock", use_container_width=True)

                    if deduct_btn:
                        item = next(i for i in inventory if i["item_name"] == selected_item)
                        if deduct_qty > item["quantity"]:
                            st.error(f"Cannot deduct {deduct_qty} — only {item['quantity']} in stock.")
                        else:
                            item["quantity"] -= deduct_qty
                            save_data(INVENTORY_FILE, inventory)
                            st.success(f"✅ Remaining stock for {selected_item}: **{item['quantity']}**")
                            st.rerun()

                # ── Completely wipe item from catalog ──
                st.markdown("---")
                st.subheader("🗑️ Delete Item Completely From Inventory")
                with st.form("delete_item_form"):
                    item_to_delete = st.selectbox("Select Catalog Item to Delete", [i["item_name"] for i in inventory])
                    confirm_delete = st.form_submit_button("🗑️ Delete From Catalog", use_container_width=True)
                    
                    if confirm_delete:
                        inventory = [i for i in inventory if i["item_name"] != item_to_delete]
                        save_data(INVENTORY_FILE, inventory)
                        st.success(f"💥 **{item_to_delete}** was entirely removed from catalog.")
                        st.rerun()
