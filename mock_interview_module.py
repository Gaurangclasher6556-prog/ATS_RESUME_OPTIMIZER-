import streamlit as st
from streamlit_ace import st_ace
import mock_interview_ai
import ai_handler

def init_session():
    defaults = {
        "cf_stage": "Setup",
        "cf_b_history": [],      # List of dicts {q: str, a: str, eval: dict}
        "cf_c_problem": None,
        "cf_c_eval": None,
        "cf_sd_scenario": None,
        "cf_sd_eval": None,
        "cf_report": None,
        "cf_b_current_q": None,
        "cf_b_current_context": None,
        "cf_b_count": 0,
        "cf_c_hints": 0,
        "cf_realtime_intel": ""
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def render_mock_interview_tab(company_name, target_role, job_description, need_resume_fn, need_jd_fn, safe_read_bytes_fn, extract_text_fn):
    init_session()
    
    st.markdown("### 🎤 CareerForge Mock Interview Module")
    st.markdown(
        '<div class="info-banner">🎯 Comprehensive 4-Stage Interview: Behavioral, Coding, System Design, and Final Report. '
        'Powered by real company insights, adaptive difficulty, and multi-dimensional evaluation.</div>',
        unsafe_allow_html=True,
    )
    
    # Navigation tabs (visual only, controlled by state or clicking)
    stages = ["Setup", "🧠 Behavioral", "💻 Coding", "🎯 System Design", "📊 Final Report"]
    
    if st.session_state["cf_stage"] == "Setup":
        st.markdown("#### Interview Settings")
        st.info("Ensure you have set your Company Name and Target Role in the sidebar, along with your Job Description.")
        do_sys_design = st.checkbox("Include System Design Round?", value=True)
        
        if st.button("🚀 Start CareerForge Interview", use_container_width=True):
            if need_resume_fn() and need_jd_fn():
                if not company_name or not target_role:
                    st.warning("Please enter a Company Name and Target Role in the sidebar.")
                else:
                    st.session_state["cf_do_sys_design"] = do_sys_design
                    with st.spinner("🔍 Gathering Real-Time Company Intelligence..."):
                        st.session_state["cf_realtime_intel"] = mock_interview_ai.gather_realtime_intelligence(company_name, target_role)
                    
                    pdf_bytes = safe_read_bytes_fn()
                    st.session_state["cf_resume_text"] = extract_text_fn(pdf_bytes)
                    st.session_state["cf_stage"] = "🧠 Behavioral"
                    st.rerun()
                    
    elif st.session_state["cf_stage"] == "🧠 Behavioral":
        st.markdown("#### 🧠 Behavioral Round (12 Questions)")
        st.progress(st.session_state["cf_b_count"] / 12)
        
        # Display history
        for idx, item in enumerate(st.session_state["cf_b_history"]):
            with st.expander(f"Q{idx+1}: {item['q'][:60]}..."):
                st.markdown(f"**Your Answer:** {item['a']}")
                ev = item['eval']
                st.markdown(f"**STAR:** {ev.get('star_score',0)}/10 | **Values:** {ev.get('values_score',0)}/10 | **Clarity:** {ev.get('clarity_score',0)}/10 | **Depth:** {ev.get('depth_score',0)}/10")
                st.info(ev.get('feedback', ''))
                
        if st.session_state["cf_b_count"] < 12:
            if st.session_state["cf_b_current_q"] is None:
                with st.spinner("Generating next adaptive question..."):
                    history_qs = [item['q'] for item in st.session_state["cf_b_history"]]
                    q_data = mock_interview_ai.generate_behavioral_question(
                        company_name, target_role, history_qs, job_description, st.session_state["cf_resume_text"],
                        realtime_intelligence=st.session_state["cf_realtime_intel"]
                    )
                    st.session_state["cf_b_current_q"] = q_data.get('question', 'Tell me about a time you faced a challenge.')
                    st.session_state["cf_b_current_context"] = q_data.get('glassdoor_context', '')
                    st.rerun()
            
            if st.session_state.get("cf_b_current_context"):
                st.info(f"🏢 **Company Context:** {st.session_state['cf_b_current_context']}")
            st.markdown(f"**Q{st.session_state['cf_b_count']+1}:** {st.session_state['cf_b_current_q']}")
            ans = st.text_area("Your Answer:", height=150, key=f"b_ans_{st.session_state['cf_b_count']}")
            
            if st.button("Submit Answer", key=f"b_sub_{st.session_state['cf_b_count']}"):
                if ans.strip():
                    with st.spinner("Evaluating across multiple dimensions..."):
                        ev = mock_interview_ai.evaluate_behavioral(st.session_state["cf_b_current_q"], ans, company_name)
                        st.session_state["cf_b_history"].append({
                            "q": st.session_state["cf_b_current_q"],
                            "a": ans,
                            "eval": ev
                        })
                        st.session_state["cf_b_count"] += 1
                        st.session_state["cf_b_current_q"] = None
                        st.session_state["cf_b_current_context"] = None
                        st.rerun()
                else:
                    st.warning("Please provide an answer.")
        else:
            st.success("Behavioral Round Complete!")
            if st.button("Proceed to Coding Round ➡️"):
                st.session_state["cf_stage"] = "💻 Coding"
                st.rerun()

    elif st.session_state["cf_stage"] == "💻 Coding":
        st.markdown("#### 💻 Coding Round (Company-Specific)")
        
        if st.session_state["cf_c_problem"] is None:
            with st.spinner("Generating unique algorithmic problem..."):
                st.session_state["cf_c_problem"] = mock_interview_ai.generate_coding_problem(
                    company_name, target_role, job_description, st.session_state["cf_resume_text"],
                    realtime_intelligence=st.session_state["cf_realtime_intel"]
                )
                st.rerun()
                
        prob = st.session_state["cf_c_problem"]
        st.markdown(f"### {prob.get('title', 'Coding Problem')}")
        st.markdown(prob.get("description", ""))
        for ex in prob.get("examples", []):
            st.code(ex)
            
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("💡 Hint 1 (Conceptual)"):
                st.session_state["cf_c_hints"] = max(st.session_state["cf_c_hints"], 1)
        with c2:
            if st.button("💡 Hint 2 (Approach)"):
                st.session_state["cf_c_hints"] = max(st.session_state["cf_c_hints"], 2)
        with c3:
            if st.button("💡 Hint 3 (Pseudocode)"):
                st.session_state["cf_c_hints"] = max(st.session_state["cf_c_hints"], 3)
                
        for i in range(1, st.session_state["cf_c_hints"] + 1):
            with st.spinner(f"Generating Hint {i}..."):
                hint_key = f"hint_text_{i}"
                if hint_key not in st.session_state:
                    st.session_state[hint_key] = mock_interview_ai.generate_hint(prob, i)
                st.info(f"**Hint {i}:** {st.session_state[hint_key]}")

        st.markdown("**Write your code below - Simulated Judge0 Execution (40+ Languages):**")
        
        # Judge0 execution implies multiple languages support
        lang_options = ["Python", "JavaScript", "Java", "C++", "C#", "Go", "Rust", "TypeScript", "Ruby", "Swift", "Kotlin", "PHP"]
        cf_language = st.selectbox("Select Language", lang_options, index=0)
        
        ace_lang = cf_language.lower().replace("c++", "c_cpp").replace("c#", "csharp")
        code = st_ace(language=ace_lang, theme="monokai", min_lines=15, key="cf_code")
        
        c_run, c_sub = st.columns(2)
        with c_run:
            if st.button("▶️ Run Test Cases (Simulated Judge0)"):
                with st.spinner(f"Executing {cf_language} code..."):
                    res = ai_handler.simulate_code_run(prob.get('description',''), code, language=cf_language)
                    st.session_state["cf_term_out"] = res.get("terminal_output", "")
        
        if "cf_term_out" in st.session_state:
            st.code(st.session_state["cf_term_out"], language="bash")
            
        with c_sub:
            if st.button("📤 Submit Final Code"):
                with st.spinner("Analyzing complexity and optimality..."):
                    st.session_state["cf_c_eval"] = mock_interview_ai.evaluate_coding(prob, code)
                    
        if st.session_state["cf_c_eval"]:
            ev = st.session_state["cf_c_eval"]
            st.success("Code Evaluated!")
            st.markdown(f"**Time Complexity:** {ev.get('time_complexity','')}")
            st.markdown(f"**Space Optimization:** {ev.get('space_optimization','')}")
            st.markdown(f"**Signal:** {ev.get('signal','')}")
            st.markdown(f"**Follow-up:** {ev.get('follow_up','')}")
            
            next_stage = "🎯 System Design" if st.session_state.get("cf_do_sys_design", True) else "📊 Final Report"
            if st.button(f"Proceed to {next_stage} ➡️"):
                st.session_state["cf_stage"] = next_stage
                st.rerun()

    elif st.session_state["cf_stage"] == "🎯 System Design":
        st.markdown("#### 🎯 System Design Round")
        
        if st.session_state["cf_sd_scenario"] is None:
            with st.spinner("Generating system design scenario..."):
                st.session_state["cf_sd_scenario"] = mock_interview_ai.generate_system_design(company_name, target_role)
                st.rerun()
                
        sd = st.session_state["cf_sd_scenario"]
        st.markdown(f"### Scenario: {sd.get('scenario', '')}")
        st.markdown(f"**Constraints:** {sd.get('constraints', '')}")
        
        ans = st.text_area("Your Architecture Design & Trade-offs:", height=300)
        if st.button("Submit Architecture"):
            if ans.strip():
                with st.spinner("Evaluating trade-offs and scalability..."):
                    st.session_state["cf_sd_eval"] = mock_interview_ai.evaluate_system_design(sd.get('scenario',''), ans)
            else:
                st.warning("Please provide an answer.")
                
        if st.session_state["cf_sd_eval"]:
            ev = st.session_state["cf_sd_eval"]
            st.success("Design Evaluated!")
            st.markdown(f"**Score:** {ev.get('score', 0)}/10")
            st.markdown(f"**Trade-offs:** {ev.get('tradeoffs_eval', '')}")
            st.markdown(f"**Scalability:** {ev.get('scalability_eval', '')}")
            
            if st.button("Proceed to Final Report ➡️"):
                st.session_state["cf_stage"] = "📊 Final Report"
                st.rerun()

    elif st.session_state["cf_stage"] == "📊 Final Report":
        st.markdown("#### 📊 CareerForge Final Report")
        
        if st.session_state["cf_report"] is None:
            with st.spinner("Compiling multi-dimensional data..."):
                b_scores = [e['eval'].get('star_score', 5) for e in st.session_state["cf_b_history"]]
                avg_b = sum(b_scores)/len(b_scores) if b_scores else 0
                st.session_state["cf_report"] = mock_interview_ai.generate_final_report(
                    avg_b, 
                    st.session_state.get("cf_c_eval", {}),
                    st.session_state.get("cf_sd_eval", {})
                )
                st.rerun()
                
        rep = st.session_state["cf_report"]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Behavioral", f"{rep.get('behavioral_score',0)}/10")
        c2.metric("Coding", f"{rep.get('coding_score',0)}/10")
        if st.session_state.get("cf_do_sys_design", True):
            c3.metric("System Design", f"{rep.get('system_design_score',0)}/10")
        c4.metric("Hire Signal", rep.get("hire_signal", "N/A"))
        
        st.markdown("### 🌟 Strengths")
        for s in rep.get("strengths", []):
            st.markdown(f"- ✅ {s}")
            
        st.markdown("### 📈 Improvement Areas")
        for i in rep.get("improvements", []):
            st.markdown(f"- ⚠️ {i}")
            
        st.markdown("### 📚 Personalized Study Plan")
        for p in rep.get("study_plan", []):
            st.markdown(f"- {p}")
            
        if st.button("🔄 Start New CareerForge Interview"):
            for key in list(st.session_state.keys()):
                if key.startswith("cf_"):
                    del st.session_state[key]
            st.rerun()
