import os
import pymysql
import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from pathlib import Path
from groq import Groq

# ---------- CONFIG ----------
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / '.env')
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

st.set_page_config(page_title='Sleep Analytics AI', page_icon='🌙', layout='wide')


def get_connection():


    return pymysql.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        port=int(os.getenv('DB_PORT', 3306)),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        charset='utf8mb4'
    )

# ---------- AI ----------
def ask_ai(system_prompt, user_prompt):


    r = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]
    )
    return r.choices[0].message.content


def generate_sleep_advice(profile):


    prompt = f"""
Age: {profile['age']}
Gender: {profile['gender']}
Sleep hours: {profile['sleep_hours']}
Quality: {profile['quality']}/10
Stress: {profile['stress']}/10
Screen time before sleep: {profile['screen']}
Caffeine mg/day: {profile['caffeine']}
Give concise practical advice in Russian.
"""
    return ask_ai('You are a sleep expert.', prompt)

# ---------- STYLE ----------
st.markdown("""
<style>
.stApp {background: linear-gradient(180deg,#0f172a,#111827); color:white;}
.block-container {padding-top:2rem;}
.title {font-size:3rem;font-weight:800;text-align:center;margin-bottom:1rem;}
.card {background:rgba(255,255,255,.05);padding:1rem;border-radius:18px;margin-bottom:1rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='title'>🌙 Sleep Analytics AI v2</div>", unsafe_allow_html=True)

# ---------- TABS ----------
tab1, tab2 = st.tabs(['💬 AI Chat', '📊 Personal Analysis'])

# ---------- TAB 1 ----------
with tab1:
    st.markdown("### Ask questions about your sleep database")
    q = st.text_input('Example: average sleep duration by gender')
    if st.button('Run analysis') and q:
        st.info('Connect your SQL + LLM query pipeline here.')
        demo = pd.DataFrame({
            'group'  :['Male' ,'Female'],
            'avg_sleep' :[6.8,7.2]
        })
        st.dataframe(demo, use_container_width=True)
        fig = px.bar(demo, x='group', y='avg_sleep', title='Average Sleep Hours')
        st.plotly_chart(fig, use_container_width=True)

# ---------- TAB 2 ----------
with tab2:
    st.markdown('### Personal Sleep Assistant')
    c1, c2 = st.columns(2)
    with c1:
        age = st.slider('Age', 18, 80, 25)
        gender = st.selectbox('Gender', ['Male', 'Female'])
        sleep_hours = st.slider('Sleep hours', 3.0, 12.0, 7.0)
        quality = st.slider('Sleep quality', 1, 10, 6)
    with c2:
        stress = st.slider('Stress level', 1, 10, 5)
        screen = st.slider('Screen time before sleep (min)', 0, 240, 60)
        caffeine = st.slider('Caffeine mg/day', 0, 600, 100)

    if st.button('✨ Get AI Advice'):
        profile = {
            'age': age,
            'gender': gender,
            'sleep_hours': sleep_hours,
            'quality': quality,
            'stress': stress,
            'screen': screen,
            'caffeine': caffeine
        }
        with st.spinner('Analyzing...'):
            advice = generate_sleep_advice(profile)
        st.markdown(f"<div class='card'>{advice}</div>", unsafe_allow_html=True)

    st.markdown('### Quick Metrics')
    m1, m2, m3 = st.columns(3)
    m1.metric('Recommended Sleep', '7-9 h')
    m2.metric('Ideal Temp', '18-20°C')
    m3.metric('Caffeine Cutoff', '8h before bed')
