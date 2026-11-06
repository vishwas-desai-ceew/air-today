"""Sectoral interventions: one card per source or policy area; each opens a
dialog with the full list of actions.

The wording is the Clean Air team's, carried over unchanged from the
previous page. Items marked `now=True` were highlighted in the original as
measures already being carried out by the government (GNCTD/DPCC), as
opposed to recommendations.
"""
from html import escape

import streamlit as st

from views.widgets import icon

INTERVENTIONS = [
    dict(
        key="hotspots", icon="eye", group="Governance",
        title="Map and mitigate hyperlocal dispersed pollution sources",
        stat=None, lede="",
        actions=[
            "Leverage the information available on citizen grievance redressal apps like SAMEER, Green Delhi App, "
            "and MCD-311 app to identify the pollution hotspots",
            "Put up a dedicated sector/hotspot-specific task force to monitor and manage the pollution hotspots.",
            "Use historical data on pollution to identify areas with recurring waste dumping and burning. Develop "
            "customised strategies to manage these chronic issues",
        ],
    ),
    dict(
        key="dss", icon="forecast", group="Governance",
        title="Make use of the Decision Support System to take pre-emptive AQ measures",
        stat=None, lede="",
        actions=[
            "CAQM's Graded Response Action Plan (GRAP) should be implemented based on the forecasted AQI level.",
            "However, we have observed that despite AQI breaching the 400 mark, CAQM does not impose higher stages "
            "(Stages 3 and 4) or GRAP.",
            "Therefore, CAQM should be more proactive in implementing the appropriate GRAP stage based on the forecasts "
            "from the Air Quality Early Warning System (AQEWS) and the Air Quality Decision Support System (AQDSS).",
        ],
    ),
    dict(
        key="transport", icon="transport", group="Sources",
        title="Transport", stat=("~40%", "of PM2.5 in Delhi from vehicles"),
        lede="Vehicular emission is one of the major air pollution sources ( ~40 per cent of PM2.5 ) in Delhi. While "
             "there are several action plans designed to reduce traffic-related air pollution, the relative impact of "
             "vehicular pollution is increasing due to the increased rate of vehicle ownership and the transient travel "
             "pattern. The regulating authorities should",
        actions=[
            "Identify the emerging traffic hotspots: With the changing land use pattern, the travel pattern, per capita "
            "trip rate and average trip lengths are also increasing. The per capita trip rate has risen by 12.3 per "
            "cent, and the average trip length has increased by 81.7 per cent between 2003 and 2023. This has brought "
            "in several emerging traffic hotspots in and around the city. The authority should monitor these "
            "traffic/congestion hotspots and design interventions to reduce on-road congestion as a short-term measure.",
            "Introduce restrictive measures like differential parking management prices to reduce private vehicle "
            "usage. Following the Supreme Court directions and implementation of the three Pilot Parking Management "
            "Action Plans (PMAPs) in Lajpat Nagar III (South Delhi Municipal Corporation), Kamla Nagar (North Delhi "
            "Municipal Corporation), and Krishna Nagar (East Delhi Municipal Corporation) in 2019, there should be "
            "efforts to scale up at city-scale or larger regions.",
            "Public transport agencies should also improve the public transport infrastructure and prioritise the "
            "quality and frequency of service and comfort as areas for improvement. The GNCTD has planned to increase "
            "frequency of service and during the winter season to encourage use of public transport. Special shuttle "
            "buses for Delhi government employees are being run on certain routes.",
            "NDMC doubled its parking charges when GRAP-II came into effect and MCD is planning to implement the same "
            "very soon. This additional enforcement is to be in place till GRAP-II measures are to be implemented.",
            "Increased monitoring when GRAP is in place for valid pollution under Control Certificate (PUCC), End of "
            "Life vehicles, visibly polluting vehicles, vehicles carrying C&D waste uncovered by the Delhi Traffic "
            "Police and imposition of fines for the defaulters",
            "Recent intervention by the GNCTD to introduce Staggered Timings for Government Offices under GNCTD and MCD "
            "that shall be effective in all offices under the Government of NCT of Delhi and the Municipal Corporation "
            "of Delhi until 28th February 2025: MCD: 8:30 AM to 5:00 PM and offices under GNCTD: 10:00 AM to 6:30 PM",
            "Encourage all private organizations in Delhi NCR to experiment options like working with 50 percent staff "
            "strength/work from home and also consider staggering of their office timings, which will help reduce "
            "traffic volume during peak office hours (directions have been drafted by DoE to circulate among all "
            "private offices, to be implemented when Stage IV (Severe+) of GRAP is in place).",
            "No entry allowed for trucks into Delhi when GRAP-IV is in place except the trucks carrying essential "
            "commodities/providing essential services and LNG,CNG,Electric, BS-VI Diesel vehicles",
            "Similarly ban imposed on plying of Delhi- Registered Diesel operated Medium Goods Vehicles (MGVs) and Heavy "
            "Goods Vehicles (HGVs) in Delhi, except those carrying essential commodities/providing essential services "
            "and no entry allowed for LCVs Registered outside Delhi, other than EVs/CNG/LNG/ BS-VI Diesel, to enter "
            "Delhi, except those carrying essential commodities/ providing essential services - during GRAP-IV",
        ],
    ),
    dict(
        key="dust", icon="dust", group="Sources",
        title="Dust (road and construction)", stat=("~11%", "of PM2.5 from road dust, excluding sources outside NCR"),
        lede="If we exclude the sources of air pollution outside Delhi NCR, road dust (including resuspended and "
             "construction dust) contributes around 11 per cent of PM2.5 concentration in Delhi. While there are "
             "several notifications to monitor and regulate, the challenges remain in both enforcing the guidelines "
             "and optimising available resources. The possible solution to combat road dust lies in",
        actions=[
            "Optimising the available resources based on their efficacy: The insufficient and fragmented "
            "implementation of dust mitigation strategies undermines the efficacy of dust mitigation strategies. While "
            "a significant portion of available NCAP funds (~64 per cent) goes to address the road dust problem, still "
            "the efficiencies of the available technologies are yet to be established. In Delhi, there are around "
            "fifty-two mechanical sweepers that cover close to 1700 km of roads and collect 150 MT of dust daily. "
            "Therefore, as a short-term measure, there should be an efficient and optimised framework to use the "
            "available resources w.r.t. scheduling the interventions based on their efficiency.",
            "Assigning responsibilities to manage road dust issues: ULBs and relevant agencies, in the long term, "
            "should create a geotagged inventory of roads which will in turn assign responsibilities of agencies for "
            "the required maintenance and management plan. Currently, the road dust mitigation strategy is fragmented "
            "and it lacks a monitoring mechanism in place to identify the potential improvement in air quality through "
            "managing road dust.",
            "Introduce self-regulation across the larger construction sites: Mandate a dust mitigation plan for all "
            "construction sites with an area above 500 sq.m. This plan must include activity-based pollutant "
            "monitoring by construction site developers, deployment of a semi-automated alert system by DPCC, and IEC "
            "activities for construction workers and owners.",
            "Increased inspection and monitoring of C&D sites 500 ≥SQM and sites <500SQM plot area and relevant action "
            "is being taken against the non-complying units",
        ],
    ),
    dict(
        key="shelters", icon="home", group="People",
        title="Build adequate heated shelters for the homeless in winter", stat=None,
        lede="Prevent biomass burning for heating by providing safe, heated shelter options.",
        actions=[
            "The urban homeless are particularly vulnerable during winter, often resorting to burning biomass for "
            "warmth, which exacerbates nighttime air pollution due to ultrafine particles",
            "Establishing public heating shelters equipped with mobile heaters powered by electricity, targeted at "
            "Delhi's urban homeless population, migrants, etc.",
            "Since establishing permanent shelters is expensive and time-consuming, temporary shelters should be "
            "established in the interim - the Delhi Urban Shelter Improvement Board has established several such "
            "shelters over the last few years.",
        ],
    ),
    dict(
        key="industry", icon="factory", group="Sources",
        title="Support clean fuel use in industries in a phase-wise manner", stat=None, lede="",
        actions=[
            "In Phase-I, a strict enforcement and complete ban on unapproved fuel1 should be implemented in all large "
            "and medium-scale red category industries in the NCR (excluding Thermal Power Plants, which may use "
            "low-sulphur coal), with at least 85 per cent CEMS data submission.",
            "In Phase II, to support the adoption of clean fuels among small-scale red and all-orange category units, "
            "a cluster-based approach can be adopted by identifying potential users and addressing their technological "
            "and financial needs through incentives or subsidies. Rational pricing and uniform access to natural gas "
            "with government support for technology transition (through subsidies and capacity building) can nudge "
            "the MSMEs to adopt clean fuels.",
            dict(text="Increased monitoring when GRAP is in place for non-complying industries and DG sets. The DG sets "
                      "found to be non-complying are sealed by the GNCTD", now=True),
        ],
    ),
    dict(
        key="crop", icon="fire", group="Sources",
        title="Promote affordable zero-burn crop residue management alternatives in neighbouring states",
        stat=("~2 lakh", "straw management machines supplied"), lede="",
        actions=[
            "In the past few years, the national and state governments have taken several measures to promote in-situ "
            "and ex-situ CRM methods to discourage farmers from burning stubble and also attempted to enforce a ban. "
            "With increased penetration and use of straw management machines, fires are declining year-on-year.",
            "The Union and State governments should also promote the use of biomass-based power plants, which can "
            "convert crop residue into energy, thereby reducing the need for burning.",
            "Besides, the focus should be on ensuring the optimal use of ~2 lakh straw management machines supplied to "
            "the custom hiring centres and farmers. Officials from agricultural departments should also encourage "
            "farmers' participation in supplying paddy straw to nearby industries to realise additional income.",
            "Further, the government should identify clear metrics such as changes in satellite-derived burnt area, "
            "area managed using in-situ methods, and quantum of stubble used by industries, to assess the prevailing "
            "gaps and scope for scaling up in the subsequent seasons.",
            "By prioritising prudent management of existing resources, behavioural change campaigns, field-level "
            "demonstrations, and facilitating dialogues by progressive farmers, states can find a way out of this menace.",
        ],
    ),
    dict(
        key="alerts", icon="megaphone", group="People",
        title="Citizen alerts in newspapers and radio", stat=None, lede="",
        actions=[
            dict(text="The GNCTD is regularly releasing alerts and relevant information to the public through "
                      "newspaper advertisements and radio jingles.", now=True),
            dict(text="Advisory against bursting of crackers, vehicular pollution and general health advisory is being "
                      "broadcasted on the radio. The GRAP Citizen Charter is published by DPCC in the newspaper "
                      "regularly.", now=True),
        ],
    ),
]
GROUPS = ["All", "Sources", "Governance", "People"]
EXTRA_ICONS = {
    "transport": '<rect x="3" y="11" width="18" height="6" rx="2"/><path d="M5 11l2-5h10l2 5"/><circle cx="7.5" cy="17.5" r="1.5"/><circle cx="16.5" cy="17.5" r="1.5"/>',
    "dust": '<path d="M3 20h18"/><path d="M5 20V10l5 3V8l5 3V6l4 2v12"/><circle cx="8" cy="4" r="1"/><circle cx="12" cy="3" r="1"/>',
    "home": '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-5h4v5"/>',
    "factory": '<path d="M2 20h20V9l-6 4V9l-6 4V5H4z"/><path d="M7 16h2M12 16h2M17 16h2"/>',
    "megaphone": '<path d="M3 11v2a1 1 0 0 0 1 1h3l6 4V6L7 10H4a1 1 0 0 0-1 1z"/><path d="M16 8a5 5 0 0 1 0 8M19 5a9 9 0 0 1 0 14"/>',
}


def _icon(name, size=22):
    if name in EXTRA_ICONS:
        return (f'<svg class="sky-icon" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
                f'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
                f'aria-hidden="true">{EXTRA_ICONS[name]}</svg>')
    return icon(name, size)


def _items(card):
    return [a if isinstance(a, dict) else dict(text=a, now=False) for a in card["actions"]]


@st.dialog("Intervention", width="large")
def intervention_dialog(key):
    card = next(c for c in INTERVENTIONS if c["key"] == key)
    items = _items(card)
    now = sum(i["now"] for i in items)
    st.markdown(
        f"<div class='int-dlg-head'><div class='int-icon'>{_icon(card['icon'], 26)}</div>"
        f"<div><div class='int-group'>{escape(card['group'])}</div>"
        f"<div class='cal-dlg-date'>{escape(card['title'])}</div></div></div>"
        + (f"<div class='int-stat-big'><b>{escape(card['stat'][0])}</b> {escape(card['stat'][1])}</div>" if card["stat"] else "")
        + (f"<p class='int-lede'>{escape(card['lede'])}</p>" if card["lede"] else "")
        + "<ol class='int-actions'>" + "".join(
            f"<li class='{'now' if i['now'] else ''}'>"
            + ("<span class='int-tag'>Under way</span>" if i["now"] else "")
            + f"{escape(i['text'])}</li>" for i in items) + "</ol>"
        + (f"<div class='int-key'><span class='int-tag'>Under way</span> marks measures the government is already "
           f"carrying out ({now} here); the rest are recommendations.</div>" if now else ""),
        unsafe_allow_html=True,
    )


def render_interventions():
    total = sum(len(c["actions"]) for c in INTERVENTIONS)
    now = sum(i["now"] for c in INTERVENTIONS for i in _items(c))
    st.markdown(
        "<div class='lrn-stats lrn-stats--3'>"
        f"<div class='lrn-stat' style='--c:#0b6bcb'><span>Areas</span><b>{len(INTERVENTIONS)}</b><small>sources and policy levers</small></div>"
        f"<div class='lrn-stat' style='--c:#7048e8'><span>Actions</span><b>{total}</b><small>recommended or in place</small></div>"
        f"<div class='lrn-stat' style='--c:#1e8e5a'><span>Under way</span><b>{now}</b><small>already being carried out</small></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    group = st.segmented_control("**Show**", options=GROUPS, default="All", key="int_group")
    group = group or "All"
    cards = [c for c in INTERVENTIONS if group == "All" or c["group"] == group]

    for row in range(0, len(cards), 2):
        cols = st.columns(2, gap="medium")
        for col, card in zip(cols, cards[row:row + 2]):
            items = _items(card)
            with col, st.container(border=True, key=f"int-card-{card['key']}"):
                stat = (f"<div class='int-stat'><b>{escape(card['stat'][0])}</b><span>{escape(card['stat'][1])}</span></div>"
                        if card["stat"] else "")
                preview = card["lede"] or items[0]["text"]
                st.markdown(
                    f"<div class='int-head'><div class='int-icon'>{_icon(card['icon'])}</div>"
                    f"<div><div class='int-group'>{escape(card['group'])}</div>"
                    f"<div class='int-title'>{escape(card['title'])}</div></div></div>{stat}"
                    f"<p class='int-preview'>{escape(preview)}</p>",
                    unsafe_allow_html=True,
                )
                n_now = sum(i["now"] for i in items)
                label = f"{len(items)} action{'s' if len(items) != 1 else ''}" + (f" · {n_now} under way" if n_now else "")
                if st.button(label, key=f"int_open_{card['key']}", icon=":material/arrow_forward:",
                             width="stretch"):
                    intervention_dialog(card["key"])
    st.caption("Compiled by the Clean Air team. Figures are as originally written; check the underlying "
               "source before citing.")
