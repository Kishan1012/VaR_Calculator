import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from scipy.stats import norm
import altair as alt
import plotly.express as px

# Page Configuration
st.set_page_config(
    page_title="VaR Calculator",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded")

# Fix for altair deprecation
try:
    alt.theme.enable("dark")
except AttributeError:
    alt.themes.enable("dark")

# Futuristic Custom CSS
st.markdown("""
<style>
    /* Main background with animated gradient */
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0a0e27 100%);
        background-size: 200% 200%;
        animation: gradientShift 15s ease infinite;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Futuristic title styling */
    h1 {
        background: linear-gradient(90deg, #00ffff, #00d4ff, #0099ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 800;
        text-shadow: 0 0 30px rgba(0, 255, 255, 0.5);
        letter-spacing: 2px;
    }
    
    /* Sidebar styling with glassmorphism */
    [data-testid="stSidebar"] {
        background: rgba(26, 31, 58, 0.7);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(0, 255, 255, 0.2);
        box-shadow: 0 8px 32px 0 rgba(0, 255, 255, 0.1);
    }
    
    /* Input fields with neon glow */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input {
        background-color: rgba(26, 31, 58, 0.8);
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 8px;
        color: #e0e0e0;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stDateInput > div > div > input:focus {
        border-color: #00ffff;
        box-shadow: 0 0 15px rgba(0, 255, 255, 0.5);
        transform: translateY(-2px);
    }
    
    /* Slider styling */
    .stSlider > div > div > div {
        background: linear-gradient(90deg, #00ffff, #0099ff);
    }
    
    /* Button with futuristic glow effect */
    .stButton > button {
        background: linear-gradient(135deg, #00ffff, #0099ff);
        color: #0a0e27;
        font-weight: 700;
        border: none;
        border-radius: 10px;
        padding: 12px 24px;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.6);
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .stButton > button:hover {
        box-shadow: 0 0 30px rgba(0, 255, 255, 0.9);
        transform: translateY(-3px);
    }
    
    /* Info boxes with glassmorphism */
    .element-container div[data-testid="stMarkdownContainer"] > div[data-testid="stMarkdown"] {
        background: rgba(26, 31, 58, 0.6);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 255, 255, 0.2);
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 16px rgba(0, 255, 255, 0.1);
    }
    
    /* Tables with futuristic styling */
    .stTable {
        background: rgba(26, 31, 58, 0.8);
        border-radius: 10px;
        border: 1px solid rgba(0, 255, 255, 0.2);
        overflow: hidden;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        color: #00ffff;
        font-weight: 700;
        text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1a1f3a;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #00ffff, #0099ff);
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #00ffff;
    }
    
    /* Add glow to section headers */
    h2, h3 {
        color: #00ffff;
        text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# VaR Class Definition
class VaR:
    def __init__(self, ticker, start_date, end_date, rolling_window, confidence_level, portfolio_val):
        self.ticker = ticker
        self.start = start_date
        self.end = end_date
        self.rolling = rolling_window
        self.conf_level = confidence_level
        self.portf_val = portfolio_val
        self.historical_var = None
        self.parametric_var = None
        
        self.data()
        
    def data(self):
        df = yf.download(self.ticker, self.start, self.end, auto_adjust=False)
        self.adj_close_df = df["Adj Close"]
        self.log_returns_df = np.log(self.adj_close_df / self.adj_close_df.shift(1))
        self.log_returns_df = self.log_returns_df.dropna()
        self.equal_weights = np.array([1 / len(self.ticker)] * len(self.ticker))
        historical_returns = (self.log_returns_df * self.equal_weights).sum(axis=1)
        self.rolling_returns = historical_returns.rolling(window=self.rolling).sum()
        self.rolling_returns = self.rolling_returns.dropna()
        self.historical_method()
        self.parametric_method()

    def historical_method(self):
        historical_VaR = -np.percentile(self.rolling_returns, 100 - (self.conf_level * 100)) * self.portf_val
        self.historical_var = historical_VaR

    def parametric_method(self):
        self.cov_matrix = self.log_returns_df.cov() * 252
        self.portfolio_std = np.sqrt(np.dot(self.equal_weights.T, np.dot(self.cov_matrix, self.equal_weights)))
        parametric_VaR = self.portfolio_std * norm.ppf(self.conf_level) * np.sqrt(self.rolling / 252) * self.portf_val
        self.parametric_var = parametric_VaR

    def plot_var_results(self, title, var_value, returns_dollar, conf_level):
        # Futuristic chart styling
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor('#0a0e27')
        ax.set_facecolor('#1a1f3a')
        
        # Create histogram with cyan gradient
        n, bins, patches = ax.hist(returns_dollar, bins=50, density=True, 
                                     color='#00ffff', alpha=0.6, edgecolor='#00d4ff')
        
        # Add gradient effect to bars
        for i, patch in enumerate(patches):
            patch.set_facecolor(plt.cm.cool(i / len(patches)))
            patch.set_alpha(0.7)
        
        ax.set_xlabel(f'{title} VaR = ${var_value:.2f}', 
                      fontsize=12, color='#00ffff', fontweight='bold')
        ax.set_ylabel('Frequency', fontsize=12, color='#00ffff', fontweight='bold')
        ax.set_title(f"Distribution of Portfolio's {self.rolling}-Day Returns ({title} VaR)", 
                     fontsize=14, color='#00ffff', fontweight='bold', pad=20)
        
        # VaR line with glow effect
        ax.axvline(-var_value, color='#ff00ff', linestyle='--', linewidth=3, 
                   label=f'VaR at {conf_level:.0%} confidence level', alpha=0.9)
        
        # Style the legend
        legend = ax.legend(facecolor='#1a1f3a', edgecolor='#00ffff', 
                          framealpha=0.8, fontsize=10)
        plt.setp(legend.get_texts(), color='#e0e0e0')
        
        # Grid with subtle cyan lines
        ax.grid(True, alpha=0.2, color='#00ffff', linestyle=':')
        
        # Spine colors
        for spine in ax.spines.values():
            spine.set_edgecolor('#00ffff')
            spine.set_linewidth(1.5)
        
        # Tick colors
        ax.tick_params(colors='#e0e0e0', which='both')
        
        plt.tight_layout()
        return plt
    
if 'recent_outputs' not in st.session_state:
    st.session_state['recent_outputs'] = []

# Main Page Heading
st.markdown("""
<div style='text-align: center; padding: 20px 0;'>
    <h1 style='font-size: 3.5em; margin-bottom: 10px;'>⚡ VALUE-AT-RISK CALCULATOR</h1>
    <p style='font-size: 1.2em; color: #00d4ff; letter-spacing: 1px;'>Advanced Portfolio Risk Analytics Platform</p>
</div>
""", unsafe_allow_html=True)


# Sidebar for User Inputs
with st.sidebar:
    st.title('⚡ VaR CALCULATOR')


    tickers = st.text_input('Enter tickers separated by space', 'AAPL MSFT GOOG').split()
    start_date = st.date_input('Start date', value=pd.to_datetime('2020-01-01'))
    end_date = st.date_input('End date', value=pd.to_datetime('today'))
    rolling_window = st.slider('Rolling window', min_value=1, max_value=252, value=20)
    confidence_level = st.slider('Confidence level', min_value=0.90, max_value=0.99, value=0.95, step=0.01)
    portfolio_val = st.number_input('Portfolio value', value=100000)
    calculate_btn = st.button('Calculate VaR')



####

def calculate_and_display_var(tickers, start_date, end_date, rolling_window, confidence_level, portfolio_val):
    var_instance = VaR(tickers, start_date, end_date, rolling_window, confidence_level, portfolio_val)
    
    # Layout for charts
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.info("Historical VaR Chart")
        historical_chart = var_instance.plot_var_results("Historical", var_instance.historical_var, var_instance.rolling_returns * var_instance.portf_val, confidence_level)
        st.pyplot(historical_chart)

    with chart_col2:
        st.info("Parametric VaR Chart")
        parametric_chart = var_instance.plot_var_results("Parametric", var_instance.parametric_var, var_instance.rolling_returns * var_instance.portf_val, confidence_level)
        st.pyplot(parametric_chart)

    # Layout for input summary and recent VaR values
    col1, col3 = st.columns([1, 1])
    
    with col1:
        st.info("Input Summary")
        st.write(f"Tickers: {tickers}")
        st.write(f"Start Date: {start_date}")
        st.write(f"End Date: {end_date}")
        st.write(f"Rolling Window: {rolling_window} days")
        st.write(f"Confidence Level: {confidence_level:.2%}")
        st.write(f"Portfolio Value: ${portfolio_val:,.2f}")


    with col3:
        st.info("VaR Calculation Output")
        data = {
            "Method": ["Historical", "Parametric"],
            "VaR Value": [f"${var_instance.historical_var:,.2f}", f"${var_instance.parametric_var:,.2f}"]
        }
        df = pd.DataFrame(data)
        st.table(df)

    st.session_state['recent_outputs'].append({
        "Historical": f"${var_instance.historical_var:,.2f}",
        "Parametric": f"${var_instance.parametric_var:,.2f}"
    })

    # Display Recent VaR Output table
    with col3:
        st.info("Previous VaR Calculation Outputs")
        # Convert the list of recent outputs to a DataFrame for display
        recent_df = pd.DataFrame(st.session_state['recent_outputs'])
        st.table(recent_df)

#####
if 'first_run' not in st.session_state or st.session_state['first_run']:
    st.session_state['first_run'] = False
    # Default values for first run
    default_tickers = 'AAPL MSFT GOOG'.split()
    default_start_date = pd.to_datetime('2020-01-01')
    default_end_date = pd.to_datetime('today')
    default_rolling_window = 20
    default_confidence_level = 0.95
    default_portfolio_val = 100000

    # Perform the default calculation
    calculate_and_display_var(default_tickers, default_start_date, default_end_date, default_rolling_window, default_confidence_level, default_portfolio_val)



# Display Results on Button Click
if calculate_btn:
    calculate_and_display_var(tickers, start_date, end_date, rolling_window, confidence_level, portfolio_val)
