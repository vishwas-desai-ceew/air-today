"""Render the published Clean Air Team briefing note."""

from time import time

import streamlit as st

GOOGLE_DOC_URL = (
    "https://docs.google.com/document/d/e/"
    "2PACX-1vS408kRB0-Gf76F_UpW8SSAa2pR0JLBXgn_Hm54vIp-a17IzqrN4-efvNDhxMVVYy-VbZmTnVabdqtM/"
    "pub?embedded=true"
)
GOOGLE_DOC_PDF_URL = GOOGLE_DOC_URL.replace("?embedded=true", "?output=pdf")


def render_google_doc():
    """Display the briefing note in the same card treatment as the IMD bulletin."""
    refresh_key = "briefing_note_refresh"
    refresh_token = st.session_state.get(refresh_key, 0)
    embedded_doc_url = f"{GOOGLE_DOC_URL}&refresh={refresh_token}"

    action_column, document_column, _ = st.columns(
        [0.18, 1.3, 0.05], vertical_alignment="top", gap="small"
    )
    with action_column:
        st.markdown(
            '<div class="briefing-note-action-label">Document controls</div>',
            unsafe_allow_html=True,
        )
        if st.button(
            "**Refresh**",
            icon=":material/refresh:",
            key="refresh_button",
            width="content",
        ):
            st.session_state[refresh_key] = int(time() * 1000)
            st.rerun()

    with document_column:
        st.markdown(
            f"""
            <section class="imd-bulletin-viewer briefing-note-viewer">
                <header class="imd-bulletin-header">
                    <div class="imd-bulletin-title">
                        <span class="imd-bulletin-icon" aria-hidden="true"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><path fill="rgb(255, 255, 255)" d="M403 378.9L239.4 96L400.6 96L564.2 378.9L403 378.9zM265.5 402.5L184.9 544L495.4 544L576 402.5L265.5 402.5zM218.1 131.4L64 402.5L144.6 544L301 272.8L218.1 131.4z"/></svg></span>
                        <div>
                            <p>CEEW Clean Air Team</p>
                            <h3>Briefing Note</h3>
                        </div>
                    </div>
                    <div class="imd-bulletin-actions">
                        <span class="imd-bulletin-updated">Published briefing document</span>
                        <a class="imd-bulletin-download" href="{GOOGLE_DOC_PDF_URL}" target="_blank" rel="noopener noreferrer"><svg xmlns="http://www.w3.org/2000/svg" height="18" width="18" viewBox="0 0 640 640"><path fill="rgb(255, 255, 255)" d="M352 96C352 78.3 337.7 64 320 64C302.3 64 288 78.3 288 96L288 306.7L246.6 265.3C234.1 252.8 213.8 252.8 201.3 265.3C188.8 277.8 188.8 298.1 201.3 310.6L297.3 406.6C309.8 419.1 330.1 419.1 342.6 406.6L438.6 310.6C451.1 298.1 451.1 277.8 438.6 265.3C426.1 252.8 405.8 252.8 393.3 265.3L352 306.7L352 96zM160 384C124.7 384 96 412.7 96 448L96 480C96 515.3 124.7 544 160 544L480 544C515.3 544 544 515.3 544 480L544 448C544 412.7 515.3 384 480 384L433.1 384L376.5 440.6C345.3 471.8 294.6 471.8 263.4 440.6L206.9 384L160 384zM464 440C477.3 440 488 450.7 488 464C488 477.3 477.3 488 464 488C450.7 488 440 477.3 440 464C440 450.7 450.7 440 464 440z"/></svg>&nbsp;Download as a PDF</a>
                    </div>
                </header>
                <div class="imd-bulletin-frame briefing-note-frame">
                    <iframe
                        title="CEEW Clean Air Team briefing note"
                        src="{embedded_doc_url}"
                        loading="lazy">
                    </iframe>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )
