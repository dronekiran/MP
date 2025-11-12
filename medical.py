import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date, timedelta
import json
import os
import time
import requests
from io import BytesIO
from PIL import Image

# Zone configuration with constituencies properly grouped by districts - FIXED to 175 constituencies
ZONE_DATA = {
    'Zone 1': {
        'Alluri Sitharama Raju': ['Araku', 'Paderu', 'Rampachodavaram'],
        'Anakapalle': ['Anakapalle', 'Chodavaram', 'Madugula', 'Narsipatnam', 'Payakaraopeta', 'Pendurthi', 'Yelamanchili'],
        'Parvathipuram Manyam': ['Kurupam', 'Palakonda', 'Parvathipuram', 'Salur'],
        'Srikakulam': ['Amadalavalasa', 'Etcherla', 'Ichapuram', 'Narasannapeta', 'Palasa', 'Pathapatnam', 'Srikakulam', 'Tekkali'],
        'Visakhapatnam': ['Bhimili', 'Gajuwaka', 'Visakhapatnam East', 'Visakhapatnam North', 'Visakhapatnam South', 'Visakhapatnam West'],
        'Vizianagaram': ['Bobbili', 'Cheepurupalli', 'Gajapathinagaram', 'Nellimarla', 'Rajam', 'Srungavarapukota', 'Vizianagaram']
    },
    'Zone 2': {
        'Dr. B.R. Ambedkar Konaseema': ['Amalapuram', 'Kothapeta', 'Mandapeta', 'Mummidivaram', 'P. Gannavaram', 'Ramachandrapuram', 'Razole'],
        'East Godavari': ['Anaparthi', 'Gopalapuram', 'Kovvur', 'Nidadavole', 'Rajahmundry City', 'Rajahmundry Rural', 'Rajanagaram'],
        'Eluru': ['Chinthalapudi', 'Denduluru', 'Eluru', 'Kaikalur', 'Nuzivid', 'Polavaram', 'Unguturu'],
        'Kakinada': ['Jaggampeta', 'Kakinada City', 'Kakinada Rural', 'Peddapuram', 'Pithapuram', 'Prathipadu', 'Tuni'],
        'West Godavari': ['Achanta', 'Bhimavaram', 'Narasapuram', 'Palacole', 'Tadepalligudem', 'Tanuku', 'Undi']
    },
    'Zone 3': {
        'Bapatla': ['Addanki', 'Bapatla', 'Chirala', 'Parchuru', 'Repalle', 'Vemuru'],
        'Guntur': ['Guntur East', 'Guntur West', 'Mangalagiri', 'Ponnur', 'Prathipadu (SC)', 'Tadikonda', 'Tenali'],
        'NTR': ['Jaggayyapeta', 'Mylavaram', 'Nandigama', 'Tiruvuru', 'Vijayawada Central', 'Vijayawada East', 'Vijayawada West'],
        'Palnadu': ['Chilakaluripeta', 'Gurajala', 'Macherla', 'Narasaraopeta', 'Pedakurapadu', 'Sattenapalli', 'Vinukonda'],
        'Krishna': ['Avanigadda', 'Gannavaram', 'Gudivada', 'Machilipatnam', 'Pamarru', 'Pedana', 'Penamaluru']
    },
    'Zone 4': {
        'Annamayya': ['Madanapalle', 'Pileru', 'Railway Kodur', 'Rajampeta', 'Rayachoty', 'Thamballapalle'],
        'Chittoor': ['Chittoor', 'Gangadhara Nellore', 'Kuppam', 'Nagari', 'Palamaneru', 'Punganur', 'Puthalapattu'],
        'Prakasam': ['Darsi', 'Giddalur', 'Kanigiri', 'Kondapi', 'Markapuram', 'Ongole', 'Santhanuthalapadu', 'Yerragondapalem'],
        'SPS Nellore': ['Atmakur', 'Kandukur', 'Kavali', 'Kovur', 'Nellore City', 'Nellore Rural', 'Sarvepalli', 'Udayagiri', 'Venkatagiri (P)'],
        'Tirupati': ['Chandragiri', 'Gudur', 'Satyavedu', 'Srikalahasti', 'Sullurpeta', 'Tirupati']
    },
    'Zone 5': {
        'Ananthapuramu': ['Ananthapur Urban', 'Gunthakal', 'Kalyandurg', 'Rayadurg', 'Singanamala', 'Tadipatri', 'Uravakonda'],
        'Kurnool': ['Adoni', 'Alur', 'Kodumur', 'Kurnool', 'Mantralayam', 'Pattikonda', 'Yemmiganur'],
        'Nandyala': ['Allagadda', 'Banaganapalle', 'Dhone', 'Nandikotkur', 'Nandyala', 'Panyam', 'Srisailam'],
        'YSR': ['Badvel', 'Jammalamadugu', 'Kadapa', 'Kamalapuram', 'Mydukur', 'Proddatur', 'Pulivendula'],
        'Sri Sathya Sai': ['Dharmavaram', 'Hindupur', 'Kadiri', 'Madakasira', 'Penukonda', 'Puttaparthi', 'Raptadu']
    }
}

# Create reverse mappings
DISTRICT_ZONE_MAPPING = {}
CONSTITUENCY_DISTRICT_MAPPING = {}
CONSTITUENCY_ZONE_MAPPING = {}

for zone, districts in ZONE_DATA.items():
    for district, constituencies in districts.items():
        DISTRICT_ZONE_MAPPING[district] = zone
        for constituency in constituencies:
            CONSTITUENCY_DISTRICT_MAPPING[constituency] = district
            CONSTITUENCY_ZONE_MAPPING[constituency] = zone

# Calculate total constituencies and districts from ZONE_DATA (Updated from 175 to 181)
TOTAL_CONSTITUENCIES = sum(len(constituencies) for districts in ZONE_DATA.values() for constituencies in districts.values())
TOTAL_DISTRICTS = sum(len(districts) for districts in ZONE_DATA.values())

# Print constituency count verification
print(f"🚨 CONSTITUENCY COUNT UPDATE: Total constituencies updated from 175 to {TOTAL_CONSTITUENCIES}")
print(f"📊 Total Districts: {TOTAL_DISTRICTS}")
print(f"📍 Total Zones: 5")

# Verify constituency counts
def verify_constituency_counts():
    """Verify and display constituency counts by district and zone"""
    zone_counts = {}
    district_counts = {}
    
    for zone, districts in ZONE_DATA.items():
        zone_total = 0
        for district, constituencies in districts.items():
            district_counts[district] = len(constituencies)
            zone_total += len(constituencies)
            print(f"📍 {zone} -> {district}: {len(constituencies)} constituencies")
        zone_counts[zone] = zone_total
        print(f"🎯 {zone} Total: {zone_total} constituencies")
    
    return zone_counts, district_counts

# Calculate counts
ZONE_COUNTS, DISTRICT_COUNTS = verify_constituency_counts()

# Page configuration
st.set_page_config(
    page_title="Medical College Dharna Tracker",
    page_icon="⚕️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize connection to Supabase
@st.cache_resource
def init_supabase():
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    return create_client(supabase_url, supabase_key)

# Function to safely check if photo_urls has valid images
def has_valid_photos(photo_urls):
    """Check if photo_urls contains valid image URLs"""
    if not photo_urls or not isinstance(photo_urls, list):
        return False
    return len(photo_urls) > 0

# Load data from Supabase - no caching for real-time data
def load_data():
    supabase = init_supabase()
    
    try:
        response = supabase.table('protest_reports').select('*').execute()
        if response.data:
            df = pd.DataFrame(response.data)
            # Convert date strings to datetime objects
            df['report_date'] = pd.to_datetime(df['report_date'])
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['updated_at'] = pd.to_datetime(df['updated_at'])
            
            # Add zone information
            df['zone'] = df['district'].map(DISTRICT_ZONE_MAPPING)
            
            # Ensure photo_urls is properly handled
            df['photo_urls'] = df['photo_urls'].apply(lambda x: x if isinstance(x, list) else [])
            
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# NEW: Generate comprehensive reports
def generate_comprehensive_reports(df):
    """Generate detailed reports by zone and constituency"""
    today = date.today()
    today_df = df[df['report_date'].dt.date == today] if not df.empty else pd.DataFrame()
    
    reports = {
        'summary': {},
        'zone_wise': {},
        'constituency_wise': {},
        'performance_analysis': {}
    }
    
    # Summary Report
    if not today_df.empty:
        reports['summary'] = {
            'total_reports': len(today_df),
            'total_participants': today_df['number_of_participants'].sum(),
            'constituencies_covered': today_df['constituency'].nunique(),
            'districts_covered': today_df['district'].nunique(),
            'zones_covered': today_df['zone'].nunique(),
            'coverage_percentage': (today_df['constituency'].nunique() / TOTAL_CONSTITUENCIES) * 100,
            'avg_participants_per_protest': today_df['number_of_participants'].mean(),
            'max_participants_single_protest': today_df['number_of_participants'].max(),
            'total_photos': today_df['photo_urls'].apply(has_valid_photos).sum()
        }
    else:
        reports['summary'] = {
            'total_reports': 0,
            'total_participants': 0,
            'constituencies_covered': 0,
            'districts_covered': 0,
            'zones_covered': 0,
            'coverage_percentage': 0,
            'avg_participants_per_protest': 0,
            'max_participants_single_protest': 0,
            'total_photos': 0
        }
    
    # Zone-wise Report
    for zone in ZONE_DATA.keys():
        zone_constituencies = ZONE_COUNTS[zone]
        
        if not today_df.empty:
            zone_data = today_df[today_df['zone'] == zone]
            zone_covered = zone_data['constituency'].nunique()
            zone_participants = zone_data['number_of_participants'].sum()
            zone_reports = len(zone_data)
            zone_avg_participants = zone_data['number_of_participants'].mean() if not zone_data.empty else 0
        else:
            zone_covered = 0
            zone_participants = 0
            zone_reports = 0
            zone_avg_participants = 0
        
        reports['zone_wise'][zone] = {
            'total_constituencies': zone_constituencies,
            'covered_constituencies': zone_covered,
            'coverage_percentage': (zone_covered / zone_constituencies) * 100,
            'total_participants': zone_participants,
            'total_reports': zone_reports,
            'districts_covered': zone_data['district'].nunique() if not today_df.empty else 0,
            'avg_participants_per_protest': zone_avg_participants,
            'pending_constituencies': zone_constituencies - zone_covered
        }
    
    # Constituency-wise Report
    all_constituencies_data = []
    for zone, districts in ZONE_DATA.items():
        for district, constituencies in districts.items():
            for constituency in constituencies:
                if not today_df.empty:
                    const_data = today_df[today_df['constituency'] == constituency]
                    has_report = not const_data.empty
                else:
                    has_report = False
                
                if has_report:
                    report_data = const_data.iloc[0]
                    constituency_info = {
                        'zone': zone,
                        'district': district,
                        'constituency': constituency,
                        'status': 'ACTIVE',
                        'participants': report_data['number_of_participants'],
                        'reports': len(const_data),
                        'location': report_data['place_of_protest'],
                        'last_update': report_data['created_at'].strftime('%H:%M'),
                        'leaders': f"{report_data.get('leader_mla', '')} {report_data.get('leader_acc', '')} {report_data.get('leader_others', '')}".strip(),
                        'has_photos': has_valid_photos(report_data.get('photo_urls', [])),
                        'remarks': report_data.get('remarks', '')
                    }
                else:
                    constituency_info = {
                        'zone': zone,
                        'district': district,
                        'constituency': constituency,
                        'status': 'PENDING',
                        'participants': 0,
                        'reports': 0,
                        'location': 'Not Reported',
                        'last_update': 'N/A',
                        'leaders': 'N/A',
                        'has_photos': False,
                        'remarks': 'Awaiting report'
                    }
                all_constituencies_data.append(constituency_info)
    
    reports['constituency_wise'] = all_constituencies_data
    
    # Performance Analysis
    active_constituencies = [c for c in all_constituencies_data if c['status'] == 'ACTIVE']
    pending_constituencies = [c for c in all_constituencies_data if c['status'] == 'PENDING']
    
    reports['performance_analysis'] = {
        'total_active': len(active_constituencies),
        'total_pending': len(pending_constituencies),
        'coverage_rate': (len(active_constituencies) / TOTAL_CONSTITUENCIES) * 100,
        'top_performing_zones': sorted([(zone, data['coverage_percentage']) for zone, data in reports['zone_wise'].items()], key=lambda x: x[1], reverse=True)[:3],
        'needs_attention_zones': sorted([(zone, data['coverage_percentage']) for zone, data in reports['zone_wise'].items()], key=lambda x: x[1])[:3],
        'constituencies_with_photos': len([c for c in active_constituencies if c['has_photos']])
    }
    
    return reports

# NEW: Print detailed reports to console
def print_detailed_reports(reports):
    """Print comprehensive reports to console"""
    print("\n" + "="*80)
    print("📊 COMPREHENSIVE DHARNA REPORT - MEDICAL COLLEGE PRIVATIZATION PROTEST")
    print("="*80)
    
    # Summary
    summary = reports['summary']
    print(f"\n🎯 SUMMARY REPORT")
    print(f"   Total Reports: {summary['total_reports']}")
    print(f"   Total Participants: {summary['total_participants']:,}")
    print(f"   Constituencies Covered: {summary['constituencies_covered']}/{TOTAL_CONSTITUENCIES}")
    print(f"   Coverage Percentage: {summary['coverage_percentage']:.1f}%")
    print(f"   Districts Covered: {summary['districts_covered']}/{TOTAL_DISTRICTS}")
    print(f"   Zones Covered: {summary['zones_covered']}/5")
    print(f"   Average Participants per Protest: {summary['avg_participants_per_protest']:.0f}")
    print(f"   Largest Single Protest: {summary['max_participants_single_protest']:,}")
    print(f"   Reports with Photos: {summary['total_photos']}")
    
    # Performance Analysis
    analysis = reports['performance_analysis']
    print(f"\n📈 PERFORMANCE ANALYSIS")
    print(f"   Overall Coverage Rate: {analysis['coverage_rate']:.1f}%")
    print(f"   Active Constituencies: {analysis['total_active']}")
    print(f"   Pending Constituencies: {analysis['total_pending']}")
    print(f"   Constituencies with Photos: {analysis['constituencies_with_photos']}")
    
    # Zone-wise Report
    print(f"\n🏢 ZONE-WISE PERFORMANCE")
    for zone, data in reports['zone_wise'].items():
        status_icon = "🟢" if data['coverage_percentage'] > 50 else "🟡" if data['coverage_percentage'] > 20 else "🔴"
        print(f"   {status_icon} {zone}:")
        print(f"      Coverage: {data['covered_constituencies']}/{data['total_constituencies']} ({data['coverage_percentage']:.1f}%)")
        print(f"      Participants: {data['total_participants']:,}")
        print(f"      Reports: {data['total_reports']}")
        print(f"      Avg Protest Size: {data['avg_participants_per_protest']:.0f}")
        print(f"      Pending: {data['pending_constituencies']} constituencies")
    
    # Top Performing Zones
    print(f"\n🏆 TOP PERFORMING ZONES")
    for zone, coverage in analysis['top_performing_zones']:
        print(f"   ✅ {zone}: {coverage:.1f}% coverage")
    
    # Zones Needing Attention
    print(f"\n🚨 ZONES NEEDING ATTENTION")
    for zone, coverage in analysis['needs_attention_zones']:
        print(f"   ⚠️  {zone}: {coverage:.1f}% coverage")
    
    # Top Performing Constituencies
    active_constituencies = [c for c in reports['constituency_wise'] if c['status'] == 'ACTIVE']
    if active_constituencies:
        print(f"\n🏆 TOP 10 PERFORMING CONSTITUENCIES (by participants)")
        sorted_constituencies = sorted(active_constituencies, key=lambda x: x['participants'], reverse=True)[:10]
        for i, const in enumerate(sorted_constituencies, 1):
            print(f"   {i:2d}. {const['constituency']} ({const['district']}) - {const['participants']:,} participants")
    
    # Critical Pending Areas
    print(f"\n⏳ CRITICAL PENDING AREAS (Zones with lowest coverage)")
    for zone, coverage in analysis['needs_attention_zones']:
        zone_data = reports['zone_wise'][zone]
        print(f"   📍 {zone}: {zone_data['pending_constituencies']} constituencies pending")
    
    print("="*80)

# NEW: Display Reports in Streamlit
def display_comprehensive_reports(df):
    st.header("📋 Comprehensive Reports & Analysis")
    
    reports = generate_comprehensive_reports(df)
    summary = reports['summary']
    analysis = reports['performance_analysis']
    
    # Print to console button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🖨️ Print Full Report to Console", use_container_width=True):
            print_detailed_reports(reports)
            st.success("Comprehensive report printed to console!")
    
    # URGENT ALERT for low coverage
    if summary['coverage_percentage'] < 10:
        st.error(f"""
        🚨 **URGENT: LOW COVERAGE ALERT**
        
        Only **{summary['coverage_percentage']:.1f}%** of constituencies are reporting! 
        **{analysis['total_pending']} constituencies** still awaiting reports.
        
        **IMMEDIATE ACTION NEEDED:** Contact District Managers and Parliament Secretaries to submit reports.
        """)
    
    # Summary Section with improved metrics
    st.subheader("🎯 Executive Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Overall Coverage", f"{summary['coverage_percentage']:.1f}%", 
                 delta=f"{summary['constituencies_covered']}/{TOTAL_CONSTITUENCIES}")
        st.metric("Total Reports", summary['total_reports'])
    
    with col2:
        st.metric("Total Participants", f"{summary['total_participants']:,}",
                 delta=f"Avg: {summary['avg_participants_per_protest']:.0f}")
        st.metric("Largest Protest", f"{summary['max_participants_single_protest']:,}")
    
    with col3:
        st.metric("Active Constituencies", summary['constituencies_covered'],
                 delta=f"{analysis['total_pending']} pending")
        st.metric("Districts Active", f"{summary['districts_covered']}/{TOTAL_DISTRICTS}")
    
    with col4:
        st.metric("Zones Active", f"{summary['zones_covered']}/5")
        st.metric("Reports with Photos", summary['total_photos'])
    
    st.markdown("---")
    
    # Performance Analysis Section
    st.subheader("📈 Performance Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info(f"**Coverage Rate:** {analysis['coverage_rate']:.1f}%")
    
    with col2:
        st.warning(f"**Pending Constituencies:** {analysis['total_pending']}")
    
    with col3:
        st.success(f"**Active with Photos:** {analysis['constituencies_with_photos']}")
    
    # Top and Bottom Zones
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**🏆 Top Performing Zones**")
        for zone, coverage in analysis['top_performing_zones']:
            st.success(f"✅ {zone}: {coverage:.1f}% coverage")
    
    with col2:
        st.write("**🚨 Zones Needing Attention**")
        for zone, coverage in analysis['needs_attention_zones']:
            st.error(f"⚠️ {zone}: {coverage:.1f}% coverage")
    
    st.markdown("---")
    
    # Zone-wise Detailed Reports
    st.subheader("🏢 Zone-wise Detailed Report")
    
    for zone, data in reports['zone_wise'].items():
        # Color code based on performance
        if data['coverage_percentage'] > 50:
            border_color = "green"
        elif data['coverage_percentage'] > 20:
            border_color = "orange"
        else:
            border_color = "red"
        
        with st.expander(f"**{zone}** - {data['covered_constituencies']}/{data['total_constituencies']} constituencies ({data['coverage_percentage']:.1f}%)", 
                        expanded=data['coverage_percentage'] < 30):  # Auto-expand low performing zones
            
            # Create columns for zone metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Coverage", f"{data['coverage_percentage']:.1f}%")
            
            with col2:
                st.metric("Participants", f"{data['total_participants']:,}")
            
            with col3:
                st.metric("Reports", data['total_reports'])
            
            with col4:
                st.metric("Avg Size", f"{data['avg_participants_per_protest']:.0f}")
            
            # Constituency details for this zone
            zone_constituencies = [c for c in reports['constituency_wise'] if c['zone'] == zone]
            active_count = len([c for c in zone_constituencies if c['status'] == 'ACTIVE'])
            pending_count = len([c for c in zone_constituencies if c['status'] == 'PENDING'])
            
            st.write(f"**Constituency Status:** {active_count} Active, {pending_count} Pending")
            
            # Show active constituencies in this zone
            active_in_zone = [c for c in zone_constituencies if c['status'] == 'ACTIVE']
            if active_in_zone:
                st.write("**Active Constituencies in this Zone:**")
                sorted_constituencies = sorted(active_in_zone, key=lambda x: x['participants'], reverse=True)
                
                # Display in a compact format
                cols = st.columns(3)
                for i, const in enumerate(sorted_constituencies):
                    col_idx = i % 3
                    with cols[col_idx]:
                        st.write(f"📍 **{const['constituency']}**")
                        st.write(f"👥 {const['participants']:,} participants")
                        if const['has_photos']:
                            st.write("📷 Has photos")
            
            # Show pending constituencies if coverage is low
            if data['coverage_percentage'] < 50:
                st.warning(f"**{pending_count} constituencies pending in {zone}**")
    
    st.markdown("---")
    
    # Download Report as CSV
    st.subheader("📥 Export Reports")
    
    # Create downloadable DataFrames
    summary_df = pd.DataFrame([reports['summary']])
    zone_df = pd.DataFrame.from_dict(reports['zone_wise'], orient='index')
    constituency_df = pd.DataFrame(reports['constituency_wise'])
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.download_button(
            label="📊 Download Summary Report (CSV)",
            data=summary_df.to_csv(index=False),
            file_name=f"dharna_summary_{date.today()}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        st.download_button(
            label="🏢 Download Zone Report (CSV)",
            data=zone_df.to_csv(),
            file_name=f"dharna_zones_{date.today()}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col3:
        st.download_button(
            label="📍 Download Constituency Report (CSV)",
            data=constituency_df.to_csv(index=False),
            file_name=f"dharna_constituencies_{date.today()}.csv",
            mime="text/csv",
            use_container_width=True
        )

# Modified display_dharna_live_tracker to show urgency
def display_dharna_live_tracker(df):
    st.header("⚡ Live Dharna Tracker - Medical College Privatization Protest")
    
    # Today's date focus
    today = date.today()
    st.info(f"🔴 **Tracking Today's State-wide Dharna Against Medical College Privatization - {today.strftime('%B %d, %Y')}**")
    
    if df.empty:
        st.warning("No dharna reports received yet. Reports will appear here as they come in.")
        return
    
    # Filter today's data
    today_df = df[df['report_date'].dt.date == today]
    
    # URGENT BANNER for low reporting
    coverage_percentage = (today_df['constituency'].nunique() / TOTAL_CONSTITUENCIES) * 100
    if coverage_percentage < 10:
        st.error(f"""
        🚨 **URGENT ACTION REQUIRED**
        
        Only **{coverage_percentage:.1f}%** of constituencies are reporting! 
        We need reports from **{TOTAL_CONSTITUENCIES - today_df['constituency'].nunique()} more constituencies**.
        
        **Please contact all District Managers immediately!**
        """)
    
    # Main Live Metrics
    st.subheader("🎯 Live Protest Metrics")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_reports = len(today_df)
        st.metric("Total Dharna Reports", total_reports)
    
    with col2:
        total_participants = today_df['number_of_participants'].sum()
        st.metric("Total Protesters", f"{total_participants:,}")
    
    with col3:
        constituencies_covered = today_df['constituency'].nunique()
        st.metric("Constituencies Active", f"{constituencies_covered}/{TOTAL_CONSTITUENCIES}", 
                 delta=f"{coverage_percentage:.1f}%")
    
    with col4:
        districts_covered = today_df['district'].nunique()
        st.metric("Districts Active", f"{districts_covered}/{TOTAL_DISTRICTS}")
    
    with col5:
        zones_covered = today_df['zone'].nunique()
        st.metric("Zones Active", f"{zones_covered}/5")
    
    st.markdown("---")
    
    # Real-time Activity Feed
    st.subheader("📱 Real-time Activity Feed")
    
    if not today_df.empty:
        # Latest reports first
        live_feed = today_df.nlargest(20, 'created_at')[[
            'created_at', 'zone', 'district', 'constituency', 'place_of_protest',
            'number_of_participants', 'leader_mla', 'leader_acc', 'leader_others'
        ]].copy()
        
        live_feed = live_feed.rename(columns={
            'created_at': 'Report Time',
            'zone': 'Zone',
            'district': 'District',
            'constituency': 'Constituency',
            'place_of_protest': 'Protest Location',
            'number_of_participants': 'Protesters',
            'leader_mla': 'MLA Leader',
            'leader_acc': 'ACC Leader',
            'leader_others': 'Other Leaders'
        })
        
        # Format timestamp
        live_feed['Report Time'] = live_feed['Report Time'].dt.strftime('%H:%M:%S')
        
        st.dataframe(
            live_feed,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Waiting for today's dharna reports to come in...")
    
    st.markdown("---")
    
    # Zone-wise Performance with urgency indicators
    st.subheader("🏢 Zone-wise Protest Status")
    
    if not today_df.empty:
        zone_summary = today_df.groupby('zone').agg({
            'id': 'count',
            'number_of_participants': 'sum',
            'district': 'nunique',
            'constituency': 'nunique'
        }).reset_index()
        
        zone_summary.columns = ['Zone', 'Reports', 'Total Protesters', 'Districts', 'Constituencies']
        
        # Add coverage percentage
        zone_summary['Total Constituencies'] = zone_summary['Zone'].map(ZONE_COUNTS)
        zone_summary['Coverage %'] = (zone_summary['Constituencies'] / zone_summary['Total Constituencies']) * 100
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Zone Performance**")
            # Color code the dataframe
            def color_coverage(val):
                if val > 50:
                    return 'background-color: green; color: white'
                elif val > 20:
                    return 'background-color: orange; color: white'
                else:
                    return 'background-color: red; color: white'
            
            styled_df = zone_summary.style.format({
                'Coverage %': '{:.1f}%',
                'Total Protesters': '{:,}'
            }).applymap(color_coverage, subset=['Coverage %'])
            
            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True
            )
        
        with col2:
            st.write("**Protesters by Zone**")
            if not zone_summary.empty:
                zone_summary_chart = zone_summary.set_index('Zone')[['Total Protesters']]
                st.bar_chart(zone_summary_chart)
            
            st.write("**Coverage by Zone**")
            if not zone_summary.empty:
                zone_coverage_chart = zone_summary.set_index('Zone')[['Coverage %']]
                st.bar_chart(zone_coverage_chart)

# [Keep all the other existing functions: display_dharna_coverage_map, display_dharna_photos, 
# display_all_constituencies_status, display_district_wise_view exactly as they were]

def display_dharna_coverage_map(df):
    st.header("🗺️ Dharna Coverage Map")
    
    today = date.today()
    today_df = df[df['report_date'].dt.date == today] if not df.empty else pd.DataFrame()
    
    # Coverage Statistics - Using FIXED totals from ZONE_DATA
    st.subheader("📊 Coverage Statistics")
    
    if not today_df.empty:
        covered_constituencies = today_df['constituency'].nunique()
        covered_districts = today_df['district'].nunique()
        covered_zones = today_df['zone'].nunique()
    else:
        covered_constituencies = covered_districts = covered_zones = 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        coverage_pct = (covered_constituencies / TOTAL_CONSTITUENCIES) * 100
        st.metric("Constituency Coverage", f"{covered_constituencies}/{TOTAL_CONSTITUENCIES}", f"{coverage_pct:.1f}%")
    
    with col2:
        district_coverage_pct = (covered_districts / TOTAL_DISTRICTS) * 100
        st.metric("District Coverage", f"{covered_districts}/{TOTAL_DISTRICTS}", f"{district_coverage_pct:.1f}%")
    
    with col3:
        zone_coverage_pct = (covered_zones / 5) * 100
        st.metric("Zone Coverage", f"{covered_zones}/5", f"{zone_coverage_pct:.1f}%")
    
    with col4:
        if not today_df.empty:
            avg_participants = today_df['number_of_participants'].mean()
            st.metric("Avg Protest Size", f"{avg_participants:.0f}")
        else:
            st.metric("Avg Protest Size", "0")
    
    # Urgent alert for low coverage
    if coverage_pct < 10:
        st.error(f"""
        🚨 **CRITICAL COVERAGE GAP**
        
        Current coverage: **{coverage_pct:.1f}%** ({covered_constituencies}/{TOTAL_CONSTITUENCIES})
        **{TOTAL_CONSTITUENCIES - covered_constituencies} constituencies** still awaiting reports!
        
        **Priority Action Required:** Focus on zones with lowest coverage.
        """)
    
    st.markdown("---")
    
    # Detailed Coverage by Zone
    st.subheader("🔍 Detailed Coverage by Zone & District")
    
    for zone in sorted(ZONE_DATA.keys()):
        zone_districts = ZONE_DATA[zone]
        
        # Calculate zone coverage using FIXED totals
        zone_constituencies = ZONE_COUNTS[zone]  # Fixed total from ZONE_DATA
        if not today_df.empty:
            zone_covered_constits = today_df[today_df['zone'] == zone]['constituency'].nunique()
        else:
            zone_covered_constits = 0
        
        zone_coverage_pct = (zone_covered_constits / zone_constituencies) * 100
        
        # Color code the expander based on coverage
        if zone_coverage_pct == 0:
            status_icon = "🔴"
        elif zone_coverage_pct < 30:
            status_icon = "🟡"
        elif zone_coverage_pct < 70:
            status_icon = "🟢"
        else:
            status_icon = "✅"
        
        with st.expander(f"{status_icon} **{zone}** - {zone_covered_constits}/{zone_constituencies} constituencies ({zone_coverage_pct:.1f}%)", 
                        expanded=zone_coverage_pct < 30):
            for district, constituencies in zone_districts.items():
                # Calculate district coverage using FIXED totals
                district_total_constits = len(constituencies)  # Fixed total from ZONE_DATA
                if not today_df.empty:
                    district_covered_constits = today_df[today_df['district'] == district]['constituency'].nunique()
                else:
                    district_covered_constits = 0
                
                district_coverage_pct = (district_covered_constits / district_total_constits) * 100
                
                # Status indicator
                if district_coverage_pct == 0:
                    status = "🔴 Not Started"
                elif district_coverage_pct < 50:
                    status = "🟡 Partial"
                elif district_coverage_pct < 100:
                    status = "🟢 Good"
                else:
                    status = "✅ Complete"
                
                st.write(f"**{district}**: {district_covered_constits}/{district_total_constits} constituencies {status}")
                
                # Show constituency status
                cols = st.columns(3)
                col_idx = 0
                for constituency in sorted(constituencies):
                    if not today_df.empty:
                        has_report = constituency in today_df[today_df['district'] == district]['constituency'].values
                    else:
                        has_report = False
                    
                    with cols[col_idx]:
                        if has_report:
                            st.success(f"✅ {constituency}")
                        else:
                            st.error(f"❌ {constituency}")
                    
                    col_idx = (col_idx + 1) % 3

# [Keep display_dharna_photos, display_all_constituencies_status, display_district_wise_view functions exactly as before]

def display_dharna_photos(df):
    st.header("📸 Live Protest Photos")
    
    today = date.today()
    today_df = df[df['report_date'].dt.date == today] if not df.empty else pd.DataFrame()
    
    if today_df.empty:
        st.info("No photos available yet. Photos will appear here as they are uploaded from protest sites.")
        return
    
    # Filter reports with photos
    photo_reports = today_df[today_df['photo_urls'].apply(has_valid_photos)]
    
    if photo_reports.empty:
        st.info("No photos uploaded yet. Waiting for photos from protest sites...")
        return
    
    # Sort by latest first
    photo_reports = photo_reports.sort_values('created_at', ascending=False)
    
    st.success(f"🎉 **Live photos from {len(photo_reports)} protest locations**")
    
    for _, report in photo_reports.iterrows():
        with st.container():
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # Protest info
                st.write(f"**📍 {report['constituency']}**")
                st.write(f"**District:** {report['district']}")
                st.write(f"**Zone:** {report['zone']}")
                st.write(f"**Location:** {report['place_of_protest']}")
                st.write(f"**Protesters:** {report['number_of_participants']:,}")
                st.write(f"**Time:** {report['created_at'].strftime('%H:%M')}")
                
                if report['leader_mla']:
                    st.write(f"**MLA Leader:** {report['leader_mla']}")
                if report['leader_acc']:
                    st.write(f"**ACC Leader:** {report['leader_acc']}")
                if report['leader_others']:
                    st.write(f"**Other Leaders:** {report['leader_others']}")
                if report['remarks']:
                    st.write(f"**Remarks:** {report['remarks']}")
            
            with col2:
                # Display photos in 2x2 grid
                photo_urls = report['photo_urls']
                if has_valid_photos(photo_urls):
                    st.write(f"**Protest Photos ({len(photo_urls)})**")
                    
                    # Create 2x2 grid
                    photos_to_show = photo_urls[:4]
                    row1 = st.columns(2)
                    row2 = st.columns(2)
                    
                    thumbnail_size = 200  # Larger thumbnails for better view
                    
                    # Row 1
                    with row1[0]:
                        if len(photos_to_show) >= 1:
                            try:
                                st.image(photos_to_show[0], width=thumbnail_size, use_column_width=False)
                            except:
                                st.error("📷 Photo loading failed")
                    
                    with row1[1]:
                        if len(photos_to_show) >= 2:
                            try:
                                st.image(photos_to_show[1], width=thumbnail_size, use_column_width=False)
                            except:
                                st.error("📷 Photo loading failed")
                    
                    # Row 2
                    with row2[0]:
                        if len(photos_to_show) >= 3:
                            try:
                                st.image(photos_to_show[2], width=thumbnail_size, use_column_width=False)
                            except:
                                st.error("📷 Photo loading failed")
                    
                    with row2[1]:
                        if len(photos_to_show) >= 4:
                            try:
                                st.image(photos_to_show[3], width=thumbnail_size, use_column_width=False)
                            except:
                                st.error("📷 Photo loading failed")
                    
                    if len(photo_urls) > 4:
                        st.info(f"📷 +{len(photo_urls) - 4} more protest photos")
            
            st.markdown("---")

def display_all_constituencies_status(df):
    st.header("📋 All Constituencies Status")
    
    today = date.today()
    today_df = df[df['report_date'].dt.date == today] if not df.empty else pd.DataFrame()
    
    # Create comprehensive status for all constituencies grouped by district
    all_constituencies_data = []
    
    for zone, districts in ZONE_DATA.items():
        for district, constituencies in districts.items():
            for constituency in constituencies:
                # Check if constituency has report
                if not today_df.empty:
                    const_report = today_df[today_df['constituency'] == constituency]
                    has_report = not const_report.empty
                else:
                    has_report = False
                
                if has_report:
                    report_data = const_report.iloc[0]
                    status = "✅ ACTIVE"
                    participants = report_data['number_of_participants']
                    location = report_data['place_of_protest']
                    last_update = report_data['created_at'].strftime('%H:%M')
                    leaders = []
                    if report_data['leader_mla']:
                        leaders.append(f"MLA: {report_data['leader_mla']}")
                    if report_data['leader_acc']:
                        leaders.append(f"ACC: {report_data['leader_acc']}")
                    if report_data['leader_others']:
                        leaders.append(f"Others: {report_data['leader_others']}")
                    leaders_str = ", ".join(leaders) if leaders else "Not specified"
                else:
                    status = "❌ PENDING"
                    participants = 0
                    location = "Awaiting report"
                    last_update = "-"
                    leaders_str = "-"
                
                all_constituencies_data.append({
                    'Zone': zone,
                    'District': district,
                    'Constituency': constituency,
                    'Status': status,
                    'Protesters': participants,
                    'Location': location,
                    'Last Update': last_update,
                    'Leaders': leaders_str
                })
    
    # Create dataframe
    status_df = pd.DataFrame(all_constituencies_data)
    
    # Display the comprehensive table
    st.dataframe(
        status_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Zone": st.column_config.TextColumn(width="small"),
            "District": st.column_config.TextColumn(width="medium"),
            "Constituency": st.column_config.TextColumn(width="medium"),
            "Status": st.column_config.TextColumn(width="small"),
            "Protesters": st.column_config.NumberColumn(format="%d", width="small"),
            "Location": st.column_config.TextColumn(width="large"),
            "Last Update": st.column_config.TextColumn(width="small"),
            "Leaders": st.column_config.TextColumn(width="large")
        }
    )
    
    # Summary with CORRECT fixed total
    active_count = len([x for x in all_constituencies_data if x['Status'] == '✅ ACTIVE'])
    pending_count = len([x for x in all_constituencies_data if x['Status'] == '❌ PENDING'])
    
    st.info(f"**Summary:** {active_count}/{TOTAL_CONSTITUENCIES} constituencies reporting dharna activities ({pending_count} pending)")

def display_district_wise_view(df):
    st.header("🏛️ District-wise Constituency View")
    
    today = date.today()
    today_df = df[df['report_date'].dt.date == today] if not df.empty else pd.DataFrame()
    
    # Create tabs for each district
    all_districts = sorted([district for zone in ZONE_DATA.values() for district in zone.keys()])
    district_tabs = st.tabs([f"**{district}**" for district in all_districts])
    
    for i, district in enumerate(all_districts):
        with district_tabs[i]:
            # Find the zone for this district
            zone = DISTRICT_ZONE_MAPPING.get(district, "Unknown")
            constituencies = []
            for z, districts in ZONE_DATA.items():
                if district in districts:
                    constituencies = districts[district]
                    break
            
            st.write(f"### {district} District")
            st.write(f"**Zone:** {zone}")
            st.write(f"**Total Constituencies:** {len(constituencies)}")
            
            # District summary
            district_data = today_df[today_df['district'] == district] if not today_df.empty else pd.DataFrame()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                reports_count = len(district_data)
                st.metric("Total Reports", reports_count)
            
            with col2:
                participants = district_data['number_of_participants'].sum() if not district_data.empty else 0
                st.metric("Total Protesters", participants)
            
            with col3:
                covered = district_data['constituency'].nunique() if not district_data.empty else 0
                st.metric("Covered", f"{covered}/{len(constituencies)}")
            
            with col4:
                coverage_pct = (covered / len(constituencies)) * 100 if len(constituencies) > 0 else 0
                st.metric("Coverage %", f"{coverage_pct:.1f}%")
            
            # Alert for low coverage
            if coverage_pct < 30:
                st.warning(f"**Low Coverage Alert:** Only {coverage_pct:.1f}% of constituencies in {district} are reporting!")
            
            st.markdown("---")
            
            # Constituency details
            st.write("### Constituency Details")
            
            constituency_data = []
            for constituency in sorted(constituencies):
                if not district_data.empty:
                    const_report = district_data[district_data['constituency'] == constituency]
                    has_report = not const_report.empty
                else:
                    has_report = False
                
                if has_report:
                    report = const_report.iloc[0]
                    status = "✅ Active"
                    participants = report['number_of_participants']
                    location = report['place_of_protest']
                    leaders = []
                    if report['leader_mla']:
                        leaders.append(report['leader_mla'])
                    if report['leader_acc']:
                        leaders.append(report['leader_acc'])
                    leaders_str = ", ".join(leaders) if leaders else "Not specified"
                else:
                    status = "❌ Pending"
                    participants = 0
                    location = "Awaiting report"
                    leaders_str = "-"
                
                constituency_data.append({
                    'Constituency': constituency,
                    'Status': status,
                    'Protesters': participants,
                    'Location': location,
                    'Leaders': leaders_str
                })
            
            # Display constituency table
            const_df = pd.DataFrame(constituency_data)
            st.dataframe(
                const_df,
                use_container_width=True,
                hide_index=True
            )

def main():
    st.title("⚕️ Medical College Privatization - State-wide Dharna Tracker")
    
    # Important banner - UPDATED CONSTITUENCY COUNT
    st.warning(f"""
    🔴 **STATE-WIDE DHARNA TODAY** - Tracking protests against medical college privatization across all {TOTAL_CONSTITUENCIES} constituencies.
    District Managers & Parliament Secretaries: Report your constituency's dharna status in real-time.
    """)
    
    # Initialize session state for auto-refresh
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = True  # Auto-refresh enabled by default for live tracking
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    if 'data' not in st.session_state:
        st.session_state.data = pd.DataFrame()
    
    # Real-time controls in sidebar
    st.sidebar.title("🔄 Live Tracking Controls")
    
    # Auto-refresh option
    auto_refresh = st.sidebar.checkbox("Auto Refresh Every 10 Seconds", value=st.session_state.auto_refresh)
    
    # Update session state
    st.session_state.auto_refresh = auto_refresh
    
    # Manual refresh button
    col1, col2 = st.sidebar.columns([2, 1])
    with col1:
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.session_state.data = pd.DataFrame()
            st.session_state.last_refresh = datetime.now()
            st.rerun()
    
    with col2:
        if st.button("Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.session_state.data = pd.DataFrame()
            st.session_state.last_refresh = datetime.now()
            st.rerun()
    
    # Last updated time
    st.sidebar.write(f"**Last Updated:** {st.session_state.last_refresh.strftime('%H:%M:%S')}")
    
    # Show total constituencies info in sidebar - USING UPDATED TOTALS
    st.sidebar.markdown("---")
    st.sidebar.info(f"**Total Coverage:**\n- {TOTAL_CONSTITUENCIES} Constituencies\n- {TOTAL_DISTRICTS} Districts\n- 5 Zones")
    
    # Load data
    if st.session_state.data.empty:
        with st.spinner('Loading live dharna data...'):
            df = load_data()
            st.session_state.data = df
    else:
        df = st.session_state.data
    
    # Auto-refresh logic - faster refresh for live event
    if st.session_state.auto_refresh:
        current_time = datetime.now()
        time_diff = (current_time - st.session_state.last_refresh).total_seconds()
        
        if time_diff >= 10:  # 10 second refresh for live event
            with st.spinner('Live updating...'):
                st.session_state.data = load_data()
                st.session_state.last_refresh = datetime.now()
                st.rerun()
        
        # Show countdown to next refresh
        time_remaining = 10 - time_diff
        st.sidebar.write(f"**Next update in:** {max(0, int(time_remaining))}s")
    
    st.sidebar.markdown("---")
    st.sidebar.title("📊 Navigation")
    
    # Navigation for dharna tracking - ADDED REPORTS PAGE
    page = st.sidebar.radio(
        "Go to:",
        ["Live Tracker", "Coverage Map", "Protest Photos", "All Constituencies", "District View", "Comprehensive Reports"]
    )
    
    if page == "Live Tracker":
        display_dharna_live_tracker(df)
    elif page == "Coverage Map":
        display_dharna_coverage_map(df)
    elif page == "Protest Photos":
        display_dharna_photos(df)
    elif page == "All Constituencies":
        display_all_constituencies_status(df)
    elif page == "District View":
        display_district_wise_view(df)
    elif page == "Comprehensive Reports":
        display_comprehensive_reports(df)

if __name__ == "__main__":
    main()