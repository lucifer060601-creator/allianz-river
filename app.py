import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

from fetch_data import fetch_allianz_nav_data
from river_calculator import calculate_river_bands

# 自動確保 Streamlit 底層 static index.html 開啟手機雙指自由縮放 (user-scalable=yes)
def ensure_mobile_zoom_enabled():
    try:
        static_index = os.path.join(os.path.dirname(st.__file__), 'static', 'index.html')
        if os.path.exists(static_index):
            with open(static_index, 'r', encoding='utf-8') as f:
                content = f.read()
            old_vp = 'content="width=device-width, initial-scale=1, shrink-to-fit=no"'
            new_vp = 'content="width=device-width, initial-scale=1.0, minimum-scale=0.5, maximum-scale=5.0, user-scalable=yes"'
            if old_vp in content:
                content = content.replace(old_vp, new_vp)
                with open(static_index, 'w', encoding='utf-8') as f:
                    f.write(content)
    except Exception:
        pass

ensure_mobile_zoom_enabled()

# Page Configuration
st.set_page_config(
    page_title="安聯台灣科技基金 淨值估值河流圖",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 即時動態注入解除手機縮放限制之 JavaScript 與雙指縮放處理 (確保全網頁與字體支援兩指縮放)
components.html("""
<script>
(function() {
    try {
        const doc = window.parent.document;
        if (!doc) return;

        // 1. 設置主視窗 Viewport 支援縮放
        let vp = doc.querySelector("meta[name='viewport']");
        if (!vp) {
            vp = doc.createElement('meta');
            vp.name = 'viewport';
            doc.head.appendChild(vp);
        }
        vp.setAttribute('content', 'width=device-width, initial-scale=1.0, minimum-scale=0.5, maximum-scale=5.0, user-scalable=yes');

        // 2. 解除所有 touch-action 限制為 auto，恢復瀏覽器原生縮放能力
        doc.documentElement.style.touchAction = 'auto';
        doc.body.style.touchAction = 'auto';

        // 3. 雙指捏合（Pinch-to-zoom）網頁與字體縮放監聽
        let currentScale = 1.0;
        let startDist = 0;
        let baseScale = 1.0;
        let isPinching = false;

        function getTarget() {
            return doc.querySelector('.stApp') || doc.body;
        }

        function applyScale(scale) {
            const target = getTarget();
            if (!target) return;
            // 允許在 0.75x ~ 3.0x 之間自由縮放
            const bounded = Math.min(Math.max(scale, 0.75), 3.0);
            currentScale = bounded;
            if ('zoom' in target.style) {
                target.style.zoom = bounded;
            } else {
                target.style.transform = 'scale(' + bounded + ')';
                target.style.transformOrigin = 'top center';
            }
        }

        function getDistance(touches) {
            const t1 = touches[0];
            const t2 = touches[1];
            return Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
        }

        function isInsidePlot(el) {
            if (!el) return false;
            return !!(
                el.closest && (
                    el.closest('.js-plotly-plot') ||
                    el.closest('[data-testid="stPlotlyChart"]') ||
                    el.closest('.plotly')
                )
            );
        }

        // 監聽雙指開始
        doc.addEventListener('touchstart', function(e) {
            if (e.touches && e.touches.length === 2) {
                // 若觸碰點在河流圖內，交給河流圖原生處理，絕不干擾河流圖！
                if (isInsidePlot(e.touches[0].target) || isInsidePlot(e.touches[1].target)) {
                    isPinching = false;
                    return;
                }
                isPinching = true;
                startDist = getDistance(e.touches);
                baseScale = currentScale;
            } else {
                isPinching = false;
            }
        }, { passive: true });

        // 監聽雙指捏合與張開
        doc.addEventListener('touchmove', function(e) {
            if (isPinching && e.touches && e.touches.length === 2) {
                if (isInsidePlot(e.touches[0].target) || isInsidePlot(e.touches[1].target)) {
                    return;
                }
                const dist = getDistance(e.touches);
                if (startDist > 0) {
                    const factor = dist / startDist;
                    applyScale(baseScale * factor);
                }
            }
        }, { passive: true });

        // 雙指離開
        doc.addEventListener('touchend', function(e) {
            if (!e.touches || e.touches.length < 2) {
                isPinching = false;
            }
        }, { passive: true });

    } catch(e) {
        console.error("Zoom handler:", e);
    }
})();
</script>
""", height=0, width=0)

# Custom CSS for Dark Aesthetics
st.markdown("""
<style>
    html, body {
        touch-action: auto !important;
        -webkit-text-size-adjust: 100% !important;
    }
    
    .stApp {
        background-color: #0e1117;
        color: #e0e6ed;
        touch-action: auto !important;
    }
    
    .hero-container {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .hero-title {
        color: #38bdf8;
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        line-height: 1.5;
    }
    .fund-badge {
        display: inline-block;
        background-color: #0369a1;
        color: #ffffff;
        font-size: 0.85rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 6px;
        margin-right: 8px;
    }
    
    .metric-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    .metric-label {
        color: #94a3b8;
        font-size: 0.9rem;
        font-weight: 500;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
    }
    .metric-neutral {
        color: #38bdf8;
    }

    /* Mobile Responsive Optimizations */
    @media (max-width: 768px) {
        html, body, .stApp, section.main {
            touch-action: auto !important;
            -webkit-overflow-scrolling: touch !important;
        }
        .hero-container {
            padding: 16px !important;
            margin-bottom: 16px !important;
        }
        .hero-title {
            font-size: 1.4rem !important;
            line-height: 1.3 !important;
        }
        .hero-subtitle {
            font-size: 0.88rem !important;
            line-height: 1.4 !important;
        }
        .metric-card {
            padding: 10px 12px !important;
            margin-bottom: 10px !important;
        }
        .metric-label {
            font-size: 0.8rem !important;
        }
        .metric-value {
            font-size: 1.25rem !important;
        }
        .fund-badge {
            font-size: 0.75rem !important;
            padding: 2px 6px !important;
            margin-bottom: 4px !important;
        }
    }

    /* Plotly Modebar & Mobile Touch Optimization */
    .modebar-container {
        opacity: 0.9 !important;
        background: transparent !important;
        padding: 2px !important;
    }
    .modebar-btn {
        padding: 4px 6px !important;
    }
    .modebar-btn svg {
        width: 17px !important;
        height: 17px !important;
    }

    .chart-tips {
        background: rgba(30, 41, 59, 0.7);
        border: 1px dashed #334155;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 0.82rem;
        color: #94a3b8;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
    }
    .tip-tag {
        background: #0284c7;
        color: white;
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Load Raw NAV Data - Always fetch latest NAV live from API on initial startup
if "df_raw" not in st.session_state:
    with st.spinner("🔄 系統啟動中，正在即時連線抓取最新淨值..."):
        try:
            df_raw = fetch_allianz_nav_data(force_update=True)
            st.session_state["df_raw"] = df_raw
        except Exception as e:
            st.error(f"載入基金數據失敗: {e}")
            st.stop()
else:
    df_raw = st.session_state["df_raw"]

try:
    min_date = df_raw['Date'].min().date()
    max_date = df_raw['Date'].max().date()
except Exception as e:
    st.error(f"解析基金日期失敗: {e}")
    st.stop()

# Header Banner
st.markdown(f"""
<div class="hero-container">
    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap;">
        <div>
            <span class="fund-badge">042004</span>
            <span class="fund-badge">ACDD04</span>
            <span class="fund-badge">台幣級別</span>
            <span class="fund-badge" style="background-color: #16a34a;">雙擊「啟動安聯科技基金河流圖.bat」即可啟動</span>
            <h1 class="hero-title" style="margin-top: 8px;">安聯台灣科技基金 動態淨值估值河流圖</h1>
            <p class="hero-subtitle">
                完整收錄自 <b>{min_date.strftime('%Y/%m/%d')} 至 {max_date.strftime('%Y/%m/%d')}</b> 之每日真實基金淨值數據。<br>
                結合 $N$ 日滾動均線 ($MA$) 與標準差 ($\sigma$) 繪製估值河流區塊，即時評估當前淨值昂貴與便宜位階。
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar Parameter Controls
st.sidebar.header("⚙️ 估值河流圖條件設定")

# 1. 時間區間選取
st.sidebar.subheader("1. 時間區間選取")
horizon_options = {
    "近 1 個月": 1,
    "近 3 個月": 3,
    "近 6 個月 (半年)": 6,
    "近 1 年": 12,
    "近 3 年": 36,
    "近 5 年": 60,
    "全期間 (成立至今)": 0
}
selected_h_label = st.sidebar.selectbox(
    "選擇時間範圍",
    options=list(horizon_options.keys()),
    index=0 # Default 1 month (近 1 個月)
)
selected_h_val = horizon_options[selected_h_label]

st.sidebar.markdown("---")

# 2. 均線週期選取 (MA Period)
st.sidebar.subheader("2. 均線週期 (MA Period)")
ma_period_options = {
    "5日 均線 (極短線)": 5,
    "10日 均線 (短線)": 10,
    "20日 均線 (月線)": 20,
    "60日 均線 (季線)": 60,
    "120日 均線 (半年線)": 120,
    "240日 均線 (年線)": 240
}
selected_ma_label = st.sidebar.selectbox(
    "選擇 N 日滾動均線週期",
    options=list(ma_period_options.keys()),
    index=0 # Default 5-day MA (5日 均線)
)
selected_ma_period = ma_period_options[selected_ma_label]

st.sidebar.markdown("---")

# Button to reload live data
if st.sidebar.button("🔄 即時連線更新淨值數據", type="primary", use_container_width=True):
    with st.spinner("正在連線抓取最新淨值..."):
        df_raw = fetch_allianz_nav_data(force_update=True)
        st.session_state["df_raw"] = df_raw
    st.toast("已為您更新最新基金歷史淨值！", icon="✅")
    st.rerun()

# Calculate Valuation River Bands
df_sub, summary = calculate_river_bands(
    df_raw,
    ma_period=selected_ma_period,
    time_horizon_months=selected_h_val
)

s = summary

# 5 KPI Metric Cards Display
st.markdown("### 📊 最新估值位階與核心指標")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">最新淨值 (NAV)</div>
        <div class="metric-value metric-neutral">${s['latest_nav']:.2f}</div>
        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">日期: {s['latest_date']}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">滾動均線 (MA {selected_ma_period}日)</div>
        <div class="metric-value metric-neutral" style="color: #cbd5e1;">${s['latest_ma']:.2f}</div>
        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">中線基準價位</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">當前估值位階</div>
        <div class="metric-value" style="color: {s['status_color']}; font-size: 1.35rem;">{s['status_str']}</div>
        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">滾動標準差σ位階</div>
    </div>
    """, unsafe_allow_html=True)

bias_val = s['bias_pct']
if s['latest_nav'] > s['latest_ma']:
    bias_class_color = "#ef4444"  # 紅字 (最新淨值大於均線)
    bias_display = f"+{abs(bias_val):.2f}%"
elif s['latest_nav'] < s['latest_ma']:
    bias_class_color = "#22c55e"  # 綠字 (最新淨值小於均線)
    bias_display = f"-{abs(bias_val):.2f}%"
else:
    bias_class_color = "#94a3b8"  # 平盤中性
    bias_display = "0.00%"

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">均線偏離率 (Bias %)</div>
        <div class="metric-value" style="color: {bias_class_color};">{bias_display}</div>
        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">相較 MA 中線之乖離率</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">2.0σ 河流價格區間</div>
        <div class="metric-value metric-neutral" style="color: #a855f7; font-size: 1.25rem;">
            ${s['lower_2']:.1f} ~ ${s['upper_2']:.1f}
        </div>
        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">便宜價 ~ 昂貴價區間</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

col_title, col_reset = st.columns([3, 1])
with col_title:
    st.markdown(f"### 📈 淨值估值河流圖分析 ({selected_ma_label} / {selected_h_label})")
with col_reset:
    if st.button("🔄 一鍵還原原圖", use_container_width=True, help="點擊立刻恢復至最初河流圖視野"):
        st.rerun()

st.markdown("""
<div class="chart-tips">
    <span class="tip-tag">📱 手機手勢</span>
    <span>👉 <b>單指滑動</b>：左右平移河流圖</span>
    <span>✌️ <b>河流圖內雙指</b>：縮放時間軸</span>
    <span>🔍 <b>河流圖外雙指</b>：兩指縮放全網頁與字體</span>
</div>
""", unsafe_allow_html=True)

fig = go.Figure()

# 1. Lower 2 Line (Baseline for cheap zone)
fig.add_trace(go.Scatter(
    x=df_sub['Date'],
    y=df_sub['Lower_2'],
    mode='lines',
    line=dict(width=0.8, color='rgba(59, 130, 246, 0.7)'),
    name='🔵 便宜區',
    hovertemplate="便宜區: $%{y:.2f}<extra></extra>"
))

# 2. Cheap Zone Fill to Lower 1 (Low zone boundary)
fig.add_trace(go.Scatter(
    x=df_sub['Date'],
    y=df_sub['Lower_1'],
    mode='lines',
    line=dict(width=0.8, color='rgba(59, 130, 246, 0.5)'),
    fill='tonexty',
    fillcolor='rgba(59, 130, 246, 0.25)',
    name='🟢 偏低區',
    hovertemplate="偏低區: $%{y:.2f}<extra></extra>"
))

# 3. Low Zone to Center MA (Green Fill)
fig.add_trace(go.Scatter(
    x=df_sub['Date'],
    y=df_sub['Center'],
    mode='lines',
    line=dict(width=1.5, color='#ffffff', dash='dash'),
    fill='tonexty',
    fillcolor='rgba(34, 197, 94, 0.20)',
    name=f'⚪ 均線 (MA {selected_ma_period}日)',
    hovertemplate="均線: $%{y:.2f}<extra></extra>"
))

# 4. High Zone (Center MA to Upper 1) - Orange Fill
fig.add_trace(go.Scatter(
    x=df_sub['Date'],
    y=df_sub['Upper_1'],
    mode='lines',
    line=dict(width=0.8, color='rgba(245, 158, 11, 0.5)'),
    fill='tonexty',
    fillcolor='rgba(245, 158, 11, 0.20)',
    name='🟠 偏高區',
    hovertemplate="偏高區: $%{y:.2f}<extra></extra>"
))

# 5. Expensive Zone (Upper 1 to Upper 2) - Red Fill
fig.add_trace(go.Scatter(
    x=df_sub['Date'],
    y=df_sub['Upper_2'],
    mode='lines',
    line=dict(width=0.8, color='rgba(239, 68, 68, 0.5)'),
    fill='tonexty',
    fillcolor='rgba(239, 68, 68, 0.25)',
    name='🔴 昂貴區',
    hovertemplate="昂貴區: $%{y:.2f}<extra></extra>"
))

# 6. Actual Fund NAV Line
fig.add_trace(go.Scatter(
    x=df_sub['Date'],
    y=df_sub['NAV'],
    mode='lines',
    line=dict(color='#38bdf8', width=2.8),
    name='基金淨值',
    hovertemplate="基金淨值: $%{y:.2f}<extra></extra>"
))

# 7. Latest Price Marker
now_year = datetime.now().year
last_d = df_sub['Date'].iloc[-1]
last_d_str = f"{last_d.year}/{last_d.month}/{last_d.day}" if last_d.year != now_year else f"{last_d.month}/{last_d.day}"
fig.add_trace(go.Scatter(
    x=[last_d],
    y=[df_sub['NAV'].iloc[-1]],
    mode='markers+text',
    text=[f" 最新: ${df_sub['NAV'].iloc[-1]:.2f} ({last_d_str})"],
    textposition="top right",
    marker=dict(color='#facc15', size=10, symbol='diamond'),
    name='最新淨值點位',
    hoverinfo='skip'
))

min_x = df_sub['Date'].min()
max_x = df_sub['Date'].max()
day_span = (max_x - min_x).days
padding_days = max(1, int(day_span * 0.03))
pad_delta = pd.Timedelta(days=padding_days)
bound_delta = pd.Timedelta(days=max(3, int(day_span * 0.20)))

min_y = float(df_sub['Lower_2'].min())
max_y = float(max(df_sub['Upper_2'].max(), df_sub['NAV'].max()))
y_pad = (max_y - min_y) * 0.06

fig.update_layout(
    title=None, # 不在圖表畫布內置標題，徹底杜絕與右上角放大縮小按鈕重疊衝突！
    xaxis=dict(
        title=None,
        tickformat="%m/%d", # 橫軸座標標籤：精簡月/日
        hoverformat="%Y/%m/%d", # 懸浮視窗頂部統一顯示完整年月日，下方不再重複
        showgrid=True,
        gridcolor="#1e293b",
        tickangle=0,
        range=[min_x - pad_delta, max_x + pad_delta],
        minallowed=min_x - bound_delta,
        maxallowed=max_x + bound_delta,
        fixedrange=False
    ),
    yaxis=dict(
        title="淨值 (NTD)",
        showgrid=True,
        gridcolor="#1e293b",
        range=[min_y - y_pad, max_y + y_pad],
        fixedrange=True # 關鍵核心：鎖定 Y 軸高度！禁止雙指縮放或滑動時將價格移出畫面，只縮放水平時間軸！
    ),
    template="plotly_dark",
    height=450,
    dragmode="pan",  # 手機觸控核心：預設為平移
    hovermode="x unified",
    margin=dict(l=10, r=10, t=15, b=85),
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.22,
        xanchor="center",
        x=0.5,
        font=dict(size=10)
    )
)

chart_config = {
    'scrollZoom': True,
    'displayModeBar': True,
    'displaylogo': False,
    'modeBarButtonsToAdd': ['zoomIn2d', 'zoomOut2d', 'resetScale2d', 'pan2d', 'zoom2d'],
    'modeBarButtonsToRemove': ['toImage', 'select2d', 'lasso2d', 'autoScale2d'],  # 徹底移除拍照功能
    'doubleClick': 'reset', # 點兩下精準還原為初始設定範圍
    'responsive': True
}

st.plotly_chart(fig, use_container_width=True, config=chart_config)

# Data Table & CSV Export Section
st.markdown("### 📋 歷史淨值與估值明細數據")

df_export = df_sub.copy()
df_export['Date_str'] = df_export['Date'].dt.strftime('%Y/%m/%d')
df_export['Bias_Pct'] = ((df_export['NAV'] - df_export['Center']) / df_export['Center'] * 100.0).round(2)

df_show = df_export[['Date_str', 'NAV', 'MA', 'Upper_2', 'Upper_1', 'Lower_1', 'Lower_2', 'Bias_Pct']].copy()
df_show = df_show.rename(columns={
    'Date_str': '交易日期',
    'NAV': '基金淨值',
    'MA': f'MA{selected_ma_period}日均線',
    'Upper_2': '昂貴上界(+2.0σ)',
    'Upper_1': '偏高上界(+1.0σ)',
    'Lower_1': '偏地下界(-1.0σ)',
    'Lower_2': '便宜下界(-2.0σ)',
    'Bias_Pct': '均線偏離率(%)'
})

col_info, col_dl = st.columns([3, 1])
with col_info:
    st.write(f"當前展示區間共有 **{len(df_show)}** 個交易日數據：")
with col_dl:
    csv_bytes = df_show.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="📥 下載明細 CSV",
        data=csv_bytes,
        file_name=f"Allianz_Tech_Fund_River_MA{selected_ma_period}_{summary['start_date']}_to_{summary['end_date']}.csv",
        mime="text/csv"
    )

st.dataframe(
    df_show,
    use_container_width=True,
    hide_index=True,
    column_config={
        "均線偏離率(%)": st.column_config.NumberColumn(
            "均線偏離率(%)",
            format="%+.2f%%"
        )
    }
)

# Footer
st.markdown("""
<hr style="border-color: #334155;">
<div style="text-align: center; color: #64748b; font-size: 0.85rem; padding-bottom: 20px;">
    數據來源：中華民國證券投資信託暨顧問商業同業公會 (SITCA) / 臺灣銀行 MoneyDJ 基金歷史淨值真實端點<br>
    本系統僅供估值與策略研究使用，過去績效不代表未來表現。
</div>
""", unsafe_allow_html=True)
