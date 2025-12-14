"""
Global CSS Styling for NL Grocery Aggregator.

This module provides load_global_styles() to inject consistent styling
across all pages. Focuses on typography, spacing, and modern card-based layouts.
"""

import streamlit as st


def load_global_styles() -> None:
    """
    Inject global CSS styles for the NL Grocery Aggregator app.
    
    This function:
    - Imports Google Fonts (Nunito) for friendly typography
    - Sets global styles for headings, paragraphs, buttons, and cards
    - Creates a slightly narrower content width on large screens
    - Applies rounded corners and subtle borders (no heavy shadows)
    - Makes sidebar clean and compact
    """
    css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&display=swap');
        
        /* Global font family */
        html, body, [class*="css"] {
            font-family: 'Nunito', 'sans serif' !important;
        }
        
        /* Headings - improved typography */
        h1, h2, h3, h4, h5, h6 {
            font-weight: 600 !important;
            letter-spacing: 0.02em !important;
        }
        
        h1 {
            font-size: 2.5rem !important;
            margin-bottom: 1rem !important;
        }
        
        h2 {
            font-size: 2rem !important;
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        h3 {
            font-size: 1.5rem !important;
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* Section spacing - tightened */
        section + section {
            margin-top: 1rem !important;
        }
        
        /* Streamlit horizontal rule (st.divider) tweak - tightened */
        hr {
            margin-top: 1rem !important;
            margin-bottom: 1rem !important;
        }
        
        /* Paragraph text with comfortable line-height */
        p, .css-1d391kg p, .stMarkdown p {
            line-height: 1.6 !important;
            margin-bottom: 0.75rem !important;
        }
        
        /* Buttons - rounded pills with subtle shadow - consistent styling */
        .stButton > button {
            border-radius: 50px !important;
            box-shadow: 0 2px 6px rgba(12, 138, 123, 0.12) !important;
            transition: all 0.3s ease !important;
            font-weight: 600 !important;
            padding: 0.5rem 1.25rem !important;
        }
        
        .stButton > button:hover {
            box-shadow: 0 3px 10px rgba(12, 138, 123, 0.2) !important;
            transform: translateY(-1px) !important;
        }
        
        /* Base card - modern with subtle border - tightened spacing */
        .nlga-card {
            border-radius: 12px !important;
            padding: 1rem 1.25rem !important;
            background-color: #ffffff !important;
            border: 1px solid rgba(12, 138, 123, 0.1) !important;
            margin-bottom: 1rem !important;
        }
        
        /* Sidebar cards - compact */
        .nlga-card--sidebar {
            padding: 0.75rem 0.875rem !important;
            border: 1px solid rgba(12, 138, 123, 0.08) !important;
        }
        
        /* Basket summary chip */
        .nlga-basket-chip {
            padding: 0.75rem 1rem !important;
            background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%) !important;
            border-left: 3px solid #0b7043 !important;
            margin-bottom: 1rem !important;
            font-size: 0.9rem !important;
        }
        
        /* Main app container: consistent width & spacing */
        .main .block-container {
            max-width: 1200px !important;
            padding-top: 1.5rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        
        /* Sidebar styling - clean and compact */
        .css-1d391kg {
            background-color: #FFF9F1 !important;
        }
        
        [data-testid="stSidebar"] {
            padding-top: 1rem !important;
        }
        
        /* Section dividers */
        .stDivider {
            margin: 1.5rem 0 !important;
        }
        
        /* Metrics styling */
        .metric-container {
            background: white;
            border-radius: 12px;
            padding: 1rem;
            border: 1px solid rgba(12, 138, 123, 0.1);
        }
        
        /* Eyebrow text (small, uppercase, muted) */
        .eyebrow-text {
            font-size: 0.75rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.1em !important;
            color: #0C8A7B !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* Pill tags */
        .pill-tag {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 50px;
            background: #E5F4F1;
            color: #0C8A7B;
            font-size: 0.75rem;
            font-weight: 600;
            margin: 0 0.25rem;
        }
        
        /* Help text styling */
        .help-text {
            color: #666 !important;
            font-size: 0.9rem !important;
            margin-top: 0.5rem !important;
        }
        
        /* Footer */
        .nlga-footer {
            margin-top: 2rem !important;
            padding: 2rem 0 1.5rem 0 !important;
            background: linear-gradient(180deg, #d9f2ea 0%, #c4e6dd 100%) !important;
            border-top-left-radius: 24px !important;
            border-top-right-radius: 24px !important;
        }
        
        .nlga-footer-inner {
            max-width: 1100px !important;
            margin: 0 auto !important;
            display: grid !important;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)) !important;
            gap: 1.5rem !important;
            font-size: 0.9rem !important;
        }
        
        .nlga-footer-col h4,
        .nlga-footer-col h5 {
            margin-bottom: 0.5rem !important;
            font-weight: 700 !important;
        }
        
        .nlga-footer-col p {
            margin: 0.25rem 0 !important;
        }
        
        .nlga-footer-col ul {
            list-style-type: none !important;
            padding-left: 0 !important;
            margin: 0 !important;
        }
        
        .nlga-footer-col li {
            margin: 0.15rem 0 !important;
        }
        
        .nlga-footer-pill {
            display: inline-block !important;
            padding: 0.2rem 0.6rem !important;
            border-radius: 999px !important;
            background-color: #0b7043 !important;
            color: #ffffff !important;
            font-size: 0.8rem !important;
        }
        
        /* Columns gap consistency */
        .css-ocqkz7, .css-1r6slb0 {
            row-gap: 1rem !important;
        }
        
        /* Metrics alignment */
        [data-testid="stMetric"] {
            padding: 0.5rem 0.25rem !important;
        }
        
        /* Page header styling - tightened spacing */
        .nlga-page-header {
            margin-bottom: 1.25rem !important;
        }
        
        .nlga-page-header h1 {
            margin-bottom: 0.25rem !important;
        }
        
        .nlga-page-header .subtitle {
            color: #666 !important;
            font-size: 1rem !important;
            font-weight: 400 !important;
        }
        
        /* Section styling - tightened spacing */
        .nlga-section {
            margin-bottom: 1.25rem !important;
        }
        
        .nlga-section-title {
            margin-bottom: 0.25rem !important;
        }
        
        .nlga-section-caption {
            color: #666 !important;
            font-size: 0.9rem !important;
            margin-bottom: 0.75rem !important;
        }
        
        /* KPI row styling */
        .nlga-kpi-row {
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        
        .nlga-kpi-item {
            flex: 1;
            padding: 1rem;
            background: white;
            border-radius: 12px;
            border: 1px solid rgba(12, 138, 123, 0.1);
        }
        
        .nlga-kpi-label {
            font-size: 0.85rem;
            color: #666;
            margin-bottom: 0.25rem;
        }
        
        .nlga-kpi-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: #0C8A7B;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

