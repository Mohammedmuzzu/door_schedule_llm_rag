import streamlit as st
import pandas as pd
import os
import threading
import subprocess

def run_qa_in_background(max_pdfs):
    # Run the script in the background
    subprocess.Popen([
        "c:\\Users\\muzaf\\my_lab\\computervision\\Scripts\\python.exe",
        "qa_benchmark.py",
        "--max-pdfs", str(max_pdfs)
    ], cwd=os.getcwd())

def render_qa_dashboard():
    st.subheader("⚖️ LLM Judge QA Benchmark")
    
    st.markdown("""
    This dashboard runs an automated end-to-end benchmark on the PDF corpus.
    It executes the extraction pipeline and then spawns an LLM Judge (GPT-4o Vision) 
    to visually cross-compare the JSON output against the PDF images to detect hallucinations and misses.
    """)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        max_pdfs = st.number_input("Max PDFs to Test", min_value=1, max_value=150, value=5, help="Testing 140 PDFs via Vision API can take an hour and cost heavily.")
        
        if st.button("🚀 Run QA Benchmark", type="primary"):
            st.info(f"Starting QA Benchmark for up to {max_pdfs} PDFs in the background. Please wait a few minutes and refresh this page.")
            run_qa_in_background(max_pdfs)
            
    with col2:
        if os.path.exists("qa_report.csv"):
            df = pd.read_csv("qa_report.csv")
            avg_acc = df["Accuracy_Score"].mean()
            failed = len(df[df["Accuracy_Score"] < 90])
            st.metric("Average Accuracy", f"{avg_acc:.1f}%")
            st.metric("Total PDFs Processed", len(df))
            st.metric("Failed Extractions (< 90%)", failed)
    
    st.divider()
    
    if os.path.exists("qa_report.csv"):
        st.markdown("#### 📄 QA Detailed Report")
        df = pd.read_csv("qa_report.csv")
        
        # Color coding rows based on accuracy
        def color_score(val):
            color = 'green' if val >= 98 else ('orange' if val >= 90 else 'red')
            return f'color: {color}'
        
        st.dataframe(
            df.style.map(color_score, subset=['Accuracy_Score']),
            use_container_width=True
        )
        
        with open("qa_report.csv", "rb") as f:
            st.download_button("⬇️ Download Full CSV Report", data=f, file_name="qa_report.csv", mime="text/csv")
    else:
        st.warning("No QA Report found. Click 'Run QA Benchmark' to generate one.")
