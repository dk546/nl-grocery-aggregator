"""
Global CSS Styling and UI Helper Functions.

This module injects custom CSS to create a fresh, healthy, light design
inspired by freasy.nl. It also provides helper functions for common UI patterns.
"""

from pathlib import Path
import random
import streamlit as st

# Assets directory for hero images
ASSETS_DIR = Path(__file__).parent.parent / "assets"


def get_asset_images() -> list[str]:
    """
    Get all image files from the assets directory.
    
    Returns:
        List of image file paths (as strings) suitable for st.image
    """
    if not ASSETS_DIR.exists():
        return []
    image_paths = sorted(
        [p for p in ASSETS_DIR.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    )
    # Return as strings (relative or absolute) suitable for st.image
    return [str(p) for p in image_paths]


def get_random_asset_image(slot_key: str) -> str | None:
    """
    Return a random image path from the assets directory, but keep it stable
    per session and per slot_key using st.session_state.
    
    Args:
        slot_key: Unique identifier for this image slot (e.g., "home_hero", "search_side")
        
    Returns:
        Image file path as string, or None if no images available
    """
    images = get_asset_images()
    if not images:
        return None
    state_key = f"nlga_asset_image_{slot_key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = random.choice(images)
    return st.session_state[state_key]


def inject_global_css() -> None:
    """
    Inject global CSS styles for the NL Grocery Aggregator app.
    
    This function:
    - Imports Google Fonts (Nunito) for friendly typography
    - Sets global styles for headings, paragraphs, buttons, and cards
    - Creates a slightly narrower content width on large screens
    - Applies rounded corners and soft shadows throughout
    """
    css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&display=swap');
        
        /* Global font family */
        html, body, [class*="css"] {
            font-family: 'Nunito', 'sans serif' !important;
        }
        
        /* Headings - bigger, semi-bold, wider letter spacing */
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
            margin-bottom: 0.75rem !important;
        }
        
        h3 {
            font-size: 1.5rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* Paragraph text with comfortable line-height */
        p, .css-1d391kg p, .stMarkdown p {
            line-height: 1.6 !important;
            margin-bottom: 0.75rem !important;
        }
        
        /* Buttons - rounded pills with subtle shadow and hover */
        .stButton > button {
            border-radius: 50px !important;
            box-shadow: 0 2px 8px rgba(12, 138, 123, 0.15) !important;
            transition: all 0.3s ease !important;
            font-weight: 600 !important;
            padding: 0.5rem 1.5rem !important;
        }
        
        .stButton > button:hover {
            box-shadow: 0 4px 12px rgba(12, 138, 123, 0.25) !important;
            transform: translateY(-1px) !important;
        }
        
        /* Cards - rounded, white background, soft shadow */
        .nlga-card {
            border-radius: 20px !important;
            background: white !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
            padding: 1.5rem !important;
            margin-bottom: 1.5rem !important;
        }
        
        /* Narrow main content width on large screens */
        .main .block-container {
            max-width: 1200px !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        
        /* Sidebar styling improvements */
        .css-1d391kg {
            background-color: #FFF9F1 !important;
        }
        
        /* Section dividers */
        .stDivider {
            margin: 2rem 0 !important;
        }
        
        /* Metrics styling */
        .metric-container {
            background: white;
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
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
        
        /* Hero section spacing */
        .hero-section {
            margin-bottom: 3rem !important;
        }
        
        /* Help text styling */
        .help-text {
            color: #666 !important;
            font-size: 0.9rem !important;
            margin-top: 0.5rem !important;
        }
        
        /* Hero banner images */
        .nlga-hero-banner img {
            border-radius: 24px !important;
            box-shadow: 0 18px 35px rgba(0, 0, 0, 0.08) !important;
            margin-top: 0.25rem !important;
            margin-bottom: 1.5rem !important;
            max-height: 260px !important;
            object-fit: cover !important;
        }
        
        /* Image card styling */
        .nlga-image-card {
            margin-bottom: 1.25rem !important;
        }
        
        .nlga-image-card img {
            border-radius: 18px !important;
            max-height: 220px !important;
            object-fit: cover !important;
        }
        
        /* Recipe card images */
        .nlga-recipe-card img {
            border-radius: 18px !important;
            max-height: 200px !important;
            object-fit: cover !important;
        }
        
        /* Footer */
        .nlga-footer {
            margin-top: 3rem !important;
            padding: 2.5rem 0 2rem 0 !important;
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
        
        /* Hero side image */
        .nlga-hero-side-image img {
            border-radius: 24px !important;
            max-height: 220px !important;
            object-fit: cover !important;
            box-shadow: 0 14px 28px rgba(0, 0, 0, 0.08) !important;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def hero_section(title: str, subtitle: str, side_image_slot: str | None = None) -> None:
    """
    Render a hero section with title, subtitle, and optional side image.
    
    Args:
        title: Main hero title
        subtitle: Subtitle/description text
        side_image_slot: Optional slot key for a side image (e.g., "home_hero_side")
    """
    st.markdown('<div class="hero-section">', unsafe_allow_html=True)
    
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.markdown(f"# {title}")
        st.markdown(f"### {subtitle}")
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        
    with col_right:
        if side_image_slot is not None:
            image_path = get_random_asset_image(side_image_slot)
            if image_path:
                st.markdown('<div class="nlga-hero-side-image">', unsafe_allow_html=True)
                st.image(image_path, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def section_header(title: str, eyebrow: str | None = None, help_text: str | None = None) -> None:
    """
    Render a section header with optional eyebrow label and help text.
    
    Args:
        title: Section title
        eyebrow: Optional small uppercase label above title (e.g., "3 SIMPLE STEPS")
        help_text: Optional muted help text below title
    """
    if eyebrow:
        st.markdown(f'<div class="eyebrow-text">{eyebrow}</div>', unsafe_allow_html=True)
    
    st.markdown(f"## {title}")
    
    if help_text:
        st.markdown(f'<div class="help-text">{help_text}</div>', unsafe_allow_html=True)


def pill_tag(text: str) -> str:
    """
    Create HTML for a small rounded pill tag (e.g., "NEW", "Plus", "Beta").
    
    Args:
        text: Text to display in the tag
    
    Returns:
        HTML string for the pill tag
    """
    return f'<span class="pill-tag">{text}</span>'


def hero_banner(slot_key: str = "default_hero") -> None:
    """
    Render a full-width hero banner image at the top of the page for the given slot key.
    
    Args:
        slot_key: Unique identifier for this hero banner slot (e.g., "home_hero", "health_hero")
    """
    image_path = get_random_asset_image(slot_key)
    if not image_path:
        return
    st.markdown('<div class="nlga-hero-banner">', unsafe_allow_html=True)
    st.image(image_path, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


def image_card(slot_key: str, caption: str | None = None) -> None:
    """
    Render a smaller marketing-style image card for sidebars or secondary columns.
    
    Args:
        slot_key: Unique identifier for this image card slot (e.g., "home_side", "basket_side")
        caption: Optional caption text to display below the image
    """
    image_path = get_random_asset_image(slot_key)
    if not image_path:
        return
    st.markdown('<div class="nlga-card nlga-image-card">', unsafe_allow_html=True)
    st.image(image_path, use_container_width=True)
    if caption:
        st.caption(caption)
    st.markdown('</div>', unsafe_allow_html=True)


def render_footer() -> None:
    """
    Render a consistent footer across all pages with brand colors and generic information.
    """
    st.markdown(
        """
        <div class="nlga-footer">
          <div class="nlga-footer-inner">
            <div class="nlga-footer-col">
              <h4>NL Grocery Aggregator</h4>
              <p>Helping Dutch households build fresh, budget-friendly baskets across Albert Heijn, Jumbo, Dirk and Picnic.</p>
            </div>
            <div class="nlga-footer-col">
              <h5>App</h5>
              <ul>
                <li>Search &amp; compare prices</li>
                <li>Smart basket &amp; health insights</li>
                <li>Recipe suggestions (beta)</li>
              </ul>
            </div>
            <div class="nlga-footer-col">
              <h5>What&apos;s coming</h5>
              <ul>
                <li>NLGA Plus with price history</li>
                <li>Personalized weekly meal plans</li>
                <li>Deeper nutrition insights</li>
              </ul>
            </div>
            <div class="nlga-footer-col">
              <h5>Contact</h5>
              <p>Demo project for learning data, APIs &amp; Streamlit.</p>
              <p><span class="nlga-footer-pill">Made in NL 🧡</span></p>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

