import streamlit as st
import subprocess
import requests
import re
import os
import signal
import time
import glob
import pandas as pd
from datetime import datetime
from PIL import Image

# ==========================================
# 0. env setting
# ==========================================
# 1. app.py location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. define bin 
BIN_DIR = os.path.join(BASE_DIR, "bin")

# 3. add bin to system PATH
os.environ["PATH"] = f"{BIN_DIR}:{os.environ.get('PATH', '')}"

try:
    if os.name == 'posix': 
        subprocess.run(f"chmod +x {BIN_DIR}/*", shell=True)
except:
    pass

# ==========================================
# 0. Setting and CSS
# ==========================================
st.set_page_config(page_title="microbiONT Analysis Platform", layout="wide")

st.markdown("""
<style>
    .stApp { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    .stChatMessageAvatar { display: none; }
    .chat-user { background-color: #E3F2FD; padding: 10px; border-radius: 10px; margin: 5px 0; text-align: right; border: 1px solid #BBDEFB; color: #0D47A1; }
    .chat-ai { background-color: #F5F5F5; padding: 10px; border-radius: 10px; margin: 5px 0; text-align: left; border: 1px solid #E0E0E0; color: #333333; }
    .stButton > button { font-weight: 600; }
    
    /* 引用文獻連結樣式 */
    .stMarkdown a {
        text-decoration: none;
        color: #0366d6;
        font-weight: bold;
    }
    .stMarkdown a:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

OLLAMA_MODEL = "microbiONT" 
OLLAMA_URL = "http://localhost:11434/api/chat"

DORADO_MODELS = ["sup", "hac", "fast"]

TRANS = {
    "zh": {
        "sidebar_title": "功能選單",
        "lang_select": "語言 (Language)",
        "tab_home": "首頁 / 關於",
        "tab_flow": "一鍵流程",
        "tab_dorado": "Basecaller",
        "tab_nanofilt": "Filter",
        "tab_porechop": "Demultiplex",
        "tab_nanoplot": "QC 報告",
        "btn_16s": "執行 16S 全流程 (+QC)",
        "btn_18s": "執行 18S 全流程 (+QC)",
        "loading_16s": "正在規劃 16S 流程...",
        "loading_18s": "正在規劃 18S 流程...",
        "model": "選擇模型 (Model)",
        "input_dir": "輸入資料夾 (Pod5)",
        "output_file": "輸出檔案 (.bam)",
        "output_fastq": "同步輸出 FASTQ",
        "chk_duplex": "啟用 Duplex (雙股校正)",
        "btn_gen_dorado": "生成 Basecaller 指令",
        "input_fastq": "輸入檔案 (.fastq)",
        "quality": "Q-Score 品質",
        "min_len": "最小長度 (bp)",
        "max_len": "最大長度 (bp)",
        "btn_gen_nanofilt": "生成 Filter 指令",
        "output_dir": "輸出目錄",
        "barcode_thresh": "Barcode 閾值 (%)",
        "barcode_diff": "Barcode 差異值",
        "btn_gen_porechop": "生成 Demultiplex 指令",
        "btn_gen_nanoplot": "生成 QC 指令",
        "btn_view_report": "檢視 QC 報告",
        "clear_cmd": "清除暫存指令",
        "chat_placeholder": "輸入對話或指令...",
        "ai_thinking": "microbiONT 正在思考...",
        "cmd_ready": "準備執行 (可編輯)",
        "btn_run": "立即執行",
        "btn_cancel": "取消",
        "status_running": "執行中 (資源已釋放)...",
        "status_success": "執行完成",
        "status_fail": "執行失敗，請檢查下方日誌",
        "status_stop": "已手動中止",
        "context_prompt": "使用者介面語言為中文。請用中文回答說明，指令保持英文。",
        "log_title": "執行日誌 (System Log)",
        "unload_ai_msg": "正在釋放 AI 資源...",
        "report_not_found": "找不到報告檔案。",
        "file_list_title": "檔案列表 (含 Reads 數)",
        "view_specific_bc": "選擇 Barcode",
        "chk_pre_qc": "Filter 前執行 QC",
        "chk_post_qc": "Filter 後執行 QC",
        "chk_indiv_qc": "個別檔案 QC (迴圈模式)",
        "stats_title": "數據統計",
        "btn_download_log": "下載完整日誌 (.txt)",
        "dorado_exe": "Dorado 程式路徑",
        "info_sop": "執行內建的標準分析流程 (SOP)。此模式不經過 AI 生成，保證指令正確。",
        "msg_16s_ready": "已載入內建 **16S 標準流程**。準備執行：\n1. Dorado (SUP)\n2. NanoFilt (Q12, 1450-1650bp)\n3. Porechop\n4. NanoPlot",
        "msg_18s_ready": "已載入內建 **18S 標準流程**。準備執行：\n1. Dorado (SUP)\n2. NanoFilt (Q12, 1800-1950bp)\n3. Porechop\n4. NanoPlot",
        "home_title": "microbiONT: Nanopore 自動化分析平台",
        "home_desc": "本軟體整合 Dorado, NanoFilt, Porechop 與 NanoPlot，提供 16S/18S 定序資料的一鍵快速分析。",
        "usage_title": "使用說明",
        "usage_content": """
        1. **一鍵流程 (One-Click)**：前往「自動化流程」分頁，點擊按鈕即可執行標準分析。
        2. **手動工具 (Manual Tools)**：使用 Basecaller, Filter, Demultiplex 等分頁手動調整參數。
        3. **對話助手 (AI Assistant)**：在下方對話框輸入需求（例如 "Q15" 或 "每個檔案跑 QC"）。
        """,
        "citation_title": "引用文獻 (Citations)",
        "citation_content": """
        若您使用本軟體進行研究，請考慮引用以下工具：

        * [Dorado](https://github.com/nanoporetech/dorado)
        * [Samtools](https://doi.org/10.1093/bioinformatics/btp352)
        * [NanoFilt](https://doi.org/10.1093/bioinformatics/bty149) 
        * [Porechop](https://github.com/rrwick/Porechop) 
        * [NanoPlot](https://doi.org/10.1093/bioinformatics/btad311)
              
        **Powered by:**
        * [Streamlit](https://streamlit.io/)
        * [Llama 3.1](https://llama.meta.com/)
        """,
        "help_model": "選擇 Basecalling 模型：\n- sup: Super Accurate (最準確，速度慢)\n- hac: High Accuracy (高準確，速度中)\n- fast: Fast (速度快，準確度較低)。",
        "help_input_dir": "存放 .pod5 原始訊號檔的資料夾路徑。",
        "help_output_file": "Basecalling 後輸出的 .bam 或 .fastq 檔名。",
        "help_duplex": "開啟 Duplex 模式。",
        "help_fastq_out": "直接輸出 .fastq 格式。",
        "help_dorado_exe": "若系統未設定環境變數，請在此輸入 dorado 執行檔的完整路徑。",
        "help_input_fastq": "要進行處理的 .fastq 序列檔案。",
        "help_q": "過濾掉平均品質低於此數值的 Reads。",
        "help_min_len": "過濾掉長度短於此數值的 Reads。",
        "help_max_len": "過濾掉長度長於此數值的 Reads。",
        "help_pre_qc": "在過濾前先跑一次 QC。",
        "help_post_qc": "在過濾後跑一次 QC。",
        "help_out_dir": "Porechop 分碼後輸出的資料夾名稱。",
        "help_thresh": "認定為該 Barcode 所需的序列匹配百分比。",
        "help_diff": "最佳匹配與次佳匹配的分數差異閾值。",
        "help_qc_in": "要進行 QC 的檔案或資料夾。",
        "help_indiv_qc": "針對資料夾內的每個 .fastq 檔單獨產生一份 QC 報告。",
        "help_fast_mode": "使用抽樣模式加速 QC 繪圖。"
    },
    "en": {
        "sidebar_title": "Menu",
        "lang_select": "Language",
        "tab_home": "Home / About",
        "tab_flow": "One-Click",
        "tab_dorado": "Basecaller",
        "tab_nanofilt": "Filter",
        "tab_porechop": "Demultiplex",
        "tab_nanoplot": "QC Report",
        "btn_16s": "Run 16S Workflow (+QC)",
        "btn_18s": "Run 18S Workflow (+QC)",
        "loading_16s": "Generating 16S command...",
        "loading_18s": "Generating 18S command...",
        "info_sop": "Execute built-in Standard Operating Procedures (SOP). This mode bypasses AI generation to ensure command accuracy.",
        "msg_16s_ready": "Loaded built-in **16S Standard Pipeline**. Ready to run:\n1. Dorado (SUP)\n2. NanoFilt (Q12, 1450-1650bp)\n3. Porechop\n4. NanoPlot",
        "msg_18s_ready": "Loaded built-in **18S Standard Pipeline**. Ready to run:\n1. Dorado (SUP)\n2. NanoFilt (Q12, 1800-1950bp)\n3. Porechop\n4. NanoPlot",
        "model": "Model",
        "input_dir": "Input Dir (Pod5)",
        "output_file": "Output File",
        "output_fastq": "Emit FASTQ",
        "chk_duplex": "Enable Duplex",
        "btn_gen_dorado": "Generate Command",
        "input_fastq": "Input File",
        "quality": "Quality (Q-Score)",
        "min_len": "Min Length (bp)",
        "max_len": "Max Length (bp)",
        "btn_gen_nanofilt": "Generate Command",
        "output_dir": "Output Directory",
        "barcode_thresh": "Threshold (%)",
        "barcode_diff": "Difference",
        "btn_gen_porechop": "Generate Command",
        "btn_gen_nanoplot": "Generate QC Command",
        "btn_view_report": "View Report",
        "clear_cmd": "Clear Buffer",
        "chat_placeholder": "Type message...",
        "ai_thinking": "microbiONT is thinking...",
        "cmd_ready": "Ready to Execute",
        "btn_run": "Run Now",
        "btn_cancel": "Cancel",
        "status_running": "Running... (Resources freed)",
        "status_success": "Completed",
        "status_fail": "Failed. Check Log.",
        "status_stop": "Stopped by User",
        "context_prompt": "User interface language is English. Please reply in English.",
        "log_title": "System Log",
        "unload_ai_msg": "Releasing AI Resources...",
        "report_not_found": "Report not found.",
        "file_list_title": "File List (Sortable)",
        "view_specific_bc": "Select Barcode",
        "chk_pre_qc": "Pre-QC",
        "chk_post_qc": "Post-QC",
        "chk_indiv_qc": "Individual QC (Loop)",
        "stats_title": "Statistics",
        "btn_download_log": "Download Log",
        "dorado_exe": "Dorado Path",
        "home_title": "microbiONT: Nanopore Analysis Platform",
        "home_desc": "Integrated platform for 16S/18S analysis using Dorado, NanoFilt, Porechop, and NanoPlot.",
        "usage_title": "Usage Guide",
        "usage_content": """
        1. **One-Click Workflow**: Go to the **Auto Workflow** tab for standard analysis.
        2. **Manual Tools**: Use tabs (Basecaller, Filter, Demultiplex) to configure parameters.
        3. **AI Assistant**: Type requirements in the chat box below.
        """,
        "citation_title": "Citations",
        "citation_content": """
        If you use this software, please cite:

        * [Dorado](https://github.com/nanoporetech/dorado)
        * [Samtools](https://doi.org/10.1093/bioinformatics/btp352)
        * [NanoFilt](https://doi.org/10.1093/bioinformatics/bty149)
        * [Porechop](https://github.com/rrwick/Porechop)
        * [NanoPlot](https://doi.org/10.1093/bioinformatics/btad311)
               
        **Powered by:**
        * [Streamlit](https://streamlit.io/)
        * [Llama 3.1](https://llama.meta.com/)
        """,
        "help_model": "Select Basecalling model.",
        "help_input_dir": "Directory containing .pod5 files.",
        "help_output_file": "Output .bam or .fastq filename.",
        "help_duplex": "Enable Duplex calling.",
        "help_fastq_out": "Convert BAM to FASTQ using samtools.",
        "help_dorado_exe": "Full path to dorado executable.",
        "help_input_fastq": "Input .fastq sequence file.",
        "help_q": "Filter reads with average quality below this score.",
        "help_min_len": "Filter reads shorter than this length.",
        "help_max_len": "Filter reads longer than this length.",
        "help_pre_qc": "Run QC before filtering.",
        "help_post_qc": "Run QC after filtering.",
        "help_out_dir": "Output directory.",
        "help_thresh": "Percentage of match required.",
        "help_diff": "Score difference required.",
        "help_qc_in": "Input file or directory for QC.",
        "help_indiv_qc": "Generate separate QC report for each file.",
        "help_fast_mode": "Use downsampling for faster QC generation."
    }
}

# State Initialization
if "messages" not in st.session_state: st.session_state.messages = []
if "pending_cmd" not in st.session_state: st.session_state.pending_cmd = ""
if "lang" not in st.session_state: st.session_state.lang = "en" 
if "last_log" not in st.session_state: st.session_state.last_log = "" 
if "is_executing" not in st.session_state: st.session_state.is_executing = False 
if "nanoplot_output_dir" not in st.session_state: st.session_state.nanoplot_output_dir = "qc_report_final"
if "porechop_output_dir" not in st.session_state: st.session_state.porechop_output_dir = "porechop_out"

def t(key):
    return TRANS[st.session_state.lang][key]

# ==========================================
# 1. 後端功能
# ==========================================

def unload_ai():
    try:
        requests.post(OLLAMA_URL, json={"model": OLLAMA_MODEL, "keep_alive": 0}, timeout=5)
        return True
    except: return False

def ask_ai(user_query, context=""):
    lang_instruction = t("context_prompt")
    final_prompt = f"Context: {context}\nSystem: {lang_instruction}\nUser Request: {user_query}"
    messages = [{"role": "user", "content": final_prompt}]
    try:
        res = requests.post(OLLAMA_URL, json={"model": OLLAMA_MODEL, "messages": messages, "stream": False}, timeout=60)
        if res.status_code == 200: return res.json()['message']['content']
        return "Error: AI Service Error"
    except Exception as e: return f"Error: {str(e)}"

def parse_mixed_response(text):
    match = re.search(r"```(?:bash|shell)?\n(.*?)\n```", text, re.DOTALL)
    if match: return True, match.group(1).strip()
    return False, None

def auto_fix_command(cmd):
    if not cmd: return cmd
    if "NanoPlot" in cmd:
        cmd = re.sub(r'--fastq\s+(\S+/)(?:\s|$)', r'--fastq \1*.fastq ', cmd)
        if "porechop_out " in cmd and "porechop_out/" not in cmd and "*.fastq" not in cmd:
             cmd = cmd.replace("porechop_out ", "porechop_out/*.fastq ")
    return cmd

def get_tool_versions():
    tools = ["dorado", "samtools", "NanoFilt", "porechop", "NanoPlot"]
    info = "=== Environment Check ===\n"
    for tool in tools:
        try:
            cmd = "NanoFilt --version" if tool == "NanoFilt" else f"{tool} --version"
            res = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode().strip().splitlines()[0]
            info += f"{tool}: {res}\n"
        except: info += f"{tool}: Not found\n"
    return info + "=======================\n"

def run_command_logic(cmd):
    version_header = get_tool_versions()
    st.session_state.last_log = version_header + f"CMD: {cmd}\n\n"
    
    st.toast(t("unload_ai_msg"))
    unload_ai()
    
    st.markdown("---")
    with st.expander(t("log_title"), expanded=True):
        live_log = st.empty()
        
    try:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, executable='/bin/bash', bufsize=1, preexec_fn=os.setsid)
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None: break
            if line:
                st.session_state.last_log += line
                live_log.code(st.session_state.last_log, language="bash")
        
        if process.returncode == 0: st.session_state.messages.append({"role": "assistant", "content": t("status_success")})
        else: 
            if process.returncode != -15: st.session_state.messages.append({"role": "assistant", "content": t("status_fail")})
    except Exception as e: st.error(f"Error: {e}")
    finally:
        st.session_state.is_executing = False
        st.rerun()

@st.cache_data(show_spinner=False)
def get_fastq_stats(path):
    try:
        size = f"{os.path.getsize(path)/(1024*1024):.2f} MB"
        cmd = f"zcat {path} | wc -l" if path.endswith(".gz") else f"wc -l {path}"
        lines = int(subprocess.check_output(cmd, shell=True).decode().split()[0])
        return size, lines // 4
    except: return "0 MB", 0

def parse_nanostats(report_dir):
    stats = {}
    path = os.path.join(report_dir, "NanoStats.txt")
    if os.path.exists(path):
        try:
            c = open(path).read()
            if m := re.search(r"Mean read quality:\s+([\d\.]+)", c): stats["Mean Q"] = m.group(1)
            if m := re.search(r"Number of reads:\s+([\d,]+)", c): stats["Reads"] = m.group(1)
            if m := re.search(r"Total bases:\s+([\d\.,]+)", c): stats["Yield"] = m.group(1)
            if m := re.search(r"Read length N50:\s+([\d,]+)", c): stats["N50"] = m.group(1)
        except: pass
    return stats

def display_qc_report(report_dir, data_dir=None):
    st.markdown("---")
    st.subheader(f"{t('stats_title')} / {t('file_list_title')}")

    if data_dir and os.path.exists(data_dir):
        files = glob.glob(f"{data_dir}/*.fastq") + glob.glob(f"{data_dir}/*.fastq.gz")
        if files:
            with st.expander(f"{t('file_list_title')} ({len(files)})", expanded=True):
                data = []
                for f in files:
                    s, r = get_fastq_stats(f)
                    data.append({"Barcode": os.path.basename(f), "Size": s, "Reads": r})
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    if not os.path.exists(report_dir):
        st.warning(t("report_not_found"))
        return

    subdirs = sorted([d for d in os.listdir(report_dir) if os.path.isdir(os.path.join(report_dir, d))])
    target = report_dir
    if subdirs:
        target = os.path.join(report_dir, st.selectbox(t("view_specific_bc"), subdirs))
    
    stats = parse_nanostats(target)
    if stats:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Mean Q", stats.get("Mean Q", "-"))
        c2.metric("Reads", stats.get("Reads", "-"))
        c3.metric("Yield", stats.get("Yield", "-"))
        c4.metric("N50", stats.get("N50", "-"))

    imgs = glob.glob(f"{target}/*.png")
    if not imgs: return
    
    priority = ["Histogram", "Yield", "LengthvsQuality"]
    summ = [i for i in imgs if any(k in os.path.basename(i) for k in priority)]
    if summ:
        cols = st.columns(2)
        for i, path in enumerate(summ[:4]):
            with cols[i%2]: st.image(Image.open(path), caption=os.path.basename(path), use_container_width=True)
            
    with st.expander("🔍 Show All Plots"):
        sel = st.selectbox("Select Plot", sorted([os.path.basename(i) for i in imgs]))
        if sel: st.image(Image.open(os.path.join(target, sel)), caption=sel)

# ==========================================
# 2. UI
# ==========================================

# --- sidebar ---
with st.sidebar:
    st.title(t("sidebar_title"))
    lang_choice = st.radio(t("lang_select"), ["中文", "English"], horizontal=True, index=0 if st.session_state.lang == "zh" else 1)
    if lang_choice == "中文": st.session_state.lang = "zh"
    else: st.session_state.lang = "en"
    st.markdown("---")
    
    # Tab
    tab_home, tab1, tab2, tab3, tab4, tab5 = st.tabs([t("tab_home"), t("tab_flow"), t("tab_dorado"), t("tab_nanofilt"), t("tab_porechop"), t("tab_nanoplot")])
    
    # [Tab 0] Home / Citation
    with tab_home:
        st.subheader(t("home_title"))
        st.write(t("home_desc"))
        st.markdown("---")
        st.write(f"### {t('usage_title')}")
        st.markdown(t("usage_content"))
        st.markdown("---")
        st.write(f"### {t('citation_title')}")
        st.markdown(t("citation_content"))

    # [Tab 1] One-Click Flow (Hardcoded SOP)
    with tab1:
        st.info(t("info_sop"))
        
        exe_path = st.session_state.get("s_d_exe", "").strip()
        dorado_cmd = exe_path if exe_path else "dorado"
        p5_in = st.session_state.get("s_d_in", "pod5/")
        pc_out = st.session_state.get("s_p_out", "porechop_out")
        qc_out = st.session_state.get("nanoplot_output_dir", "qc_report_final")

        if st.button(t("btn_16s"), use_container_width=True, key="btn_flow_16s"):
            q_val = 12
            min_l = 1450
            max_l = 1650
            cmd_1 = f"{dorado_cmd} basecaller sup {p5_in} > calls.bam"
            cmd_2 = "samtools fastq calls.bam > calls.fastq"
            cmd_3 = f"cat calls.fastq | NanoFilt -q {q_val} -l {min_l} --maxlength {max_l} --readtype 1D > filtered.fastq"
            cmd_4 = f"porechop -i filtered.fastq -b {pc_out} --barcode_threshold 75 --barcode_diff 1"
            cmd_5 = f"NanoPlot --fastq {pc_out}/*.fastq -o {qc_out} --legacy hex dot"
            full_cmd = f"{cmd_1} && {cmd_2} && {cmd_3} && {cmd_4} && {cmd_5}"
            
            st.session_state.messages.append({"role": "assistant", "content": t("msg_16s_ready")})
            st.session_state.pending_cmd = auto_fix_command(full_cmd)

        if st.button(t("btn_18s"), use_container_width=True, key="btn_flow_18s"):
            q_val = 12
            min_l = 1800
            max_l = 1950
            cmd_1 = f"{dorado_cmd} basecaller sup {p5_in} > calls.bam"
            cmd_2 = "samtools fastq calls.bam > calls.fastq"
            cmd_3 = f"cat calls.fastq | NanoFilt -q {q_val} -l {min_l} --maxlength {max_l} --readtype 1D > filtered.fastq"
            cmd_4 = f"porechop -i filtered.fastq -b {pc_out} --barcode_threshold 75 --barcode_diff 1"
            cmd_5 = f"NanoPlot --fastq {pc_out}/*.fastq -o {qc_out} --legacy hex dot"
            full_cmd = f"{cmd_1} && {cmd_2} && {cmd_3} && {cmd_4} && {cmd_5}"
            
            st.session_state.messages.append({"role": "assistant", "content": t("msg_18s_ready")})
            st.session_state.pending_cmd = auto_fix_command(full_cmd)

    # [Tab 2] Dorado
    with tab2:
        d_model = st.selectbox(t("model"), DORADO_MODELS, index=0, help=t("help_model"))
        d_in = st.text_input(t("input_dir"), "pod5/", key="s_d_in", help=t("help_input_dir"))
        d_out = st.text_input(t("output_file"), "calls.bam", key="s_d_out", help=t("help_output_file"))
        
        d_duplex = st.checkbox(t("chk_duplex"), value=False, help=t("help_duplex"))
        d_fastq = st.checkbox(t("output_fastq"), value=True, help=t("help_fastq_out"))
        d_exe = st.text_input(t("dorado_exe"), "", placeholder="/path/to/dorado", help=t("help_dorado_exe"))
        
        if st.button(t("btn_gen_dorado"), use_container_width=True, key="btn_dorado_gen"):
            exe = d_exe.strip() if d_exe.strip() else "dorado"
            mode_cmd = "duplex" if d_duplex else "basecaller"
            base_name = os.path.splitext(d_out)[0]
            bam_filename = f"{base_name}.bam"
            fastq_filename = f"{base_name}.fastq"
            
            cmd = f"{exe} {mode_cmd} {d_model} {d_in} > {bam_filename}"
            if d_fastq:
                cmd += f" && samtools fastq {bam_filename} > {fastq_filename}"
                st.toast(f"Plan: {bam_filename} -> {fastq_filename}")
            else:
                st.toast(f"Plan: {bam_filename}")
                
            st.session_state.pending_cmd = auto_fix_command(cmd)

    # [Tab 3] NanoFilt
    with tab3:
        n_in = st.text_input(t("input_fastq"), "calls.fastq", key="s_n_in", help=t("help_input_fastq"))
        n_out = st.text_input(t("output_dir"), "filtered.fastq", key="s_n_out", help=t("help_output_file"))
        n_q = st.slider(t("quality"), 5, 30, 12, help=t("help_q"))
        
        c1, c2 = st.columns(2)
        with c1: n_l = st.number_input(t("min_len"), 0, 10000, 1450, help=t("help_min_len"))
        with c2: n_max = st.number_input(t("max_len"), 0, 10000, 1650, help=t("help_max_len"))
        
        st.markdown("---")
        do_pre = st.checkbox(t("chk_pre_qc"), False, help=t("help_pre_qc"))
        do_post = st.checkbox(t("chk_post_qc"), False, help=t("help_post_qc"))
        
        if st.button(t("btn_gen_nanofilt"), use_container_width=True, key="btn_nanofilt_gen"):
            cmds = []
            if do_pre: cmds.append(f"NanoPlot --fastq {n_in} -o {os.path.splitext(n_in)[0]}_pre_qc --legacy hex dot")
            cmds.append(f"cat {n_in} | NanoFilt -q {n_q} -l {n_l} --maxlength {n_max} --readtype 1D > {n_out}")
            if do_post: cmds.append(f"NanoPlot --fastq {n_out} -o {os.path.splitext(n_out)[0]}_post_qc --legacy hex dot")
            st.session_state.pending_cmd = auto_fix_command(" && ".join(cmds))

    # [Tab 4] Porechop
    with tab4:
        p_in = st.text_input(t("input_fastq"), "filtered.fastq", key="s_p_in", help=t("help_input_fastq"))
        p_out = st.text_input(t("output_dir"), "porechop_out", key="s_p_out", help=t("help_out_dir"))
        st.session_state.porechop_output_dir = p_out
        p_tr = st.slider(t("barcode_thresh"), 0, 100, 75, help=t("help_thresh"))
        p_diff = st.number_input(t("barcode_diff"), 0, 10, 1, help=t("help_diff"))
        
        if st.button(t("btn_gen_porechop"), use_container_width=True, key="btn_porechop_gen"):
            st.session_state.pending_cmd = auto_fix_command(f"porechop -i {p_in} -b {p_out} --barcode_threshold {p_tr} --barcode_diff {p_diff}")

    # [Tab 5] NanoPlot
    with tab5:
        qc_in = st.text_input("Input", "porechop_out/", key="qc_in", help=t("help_qc_in"))
        qc_out = st.text_input("Output Report", "qc_report_final", key="qc_out")
        st.session_state.nanoplot_output_dir = qc_out
        do_indiv = st.checkbox(t("chk_indiv_qc"), False, help=t("help_indiv_qc"))
        
        if st.button(t("btn_gen_nanoplot"), use_container_width=True, key="btn_nanoplot_gen"):
            if do_indiv:
                src = qc_in.rstrip("/")
                pat = os.path.join(src, "*.fastq") if not src.endswith("q") else src
                cmd = f"mkdir -p {qc_out} && for f in {pat}; do bn=$(basename \"$f\" .fastq); NanoPlot --fastq \"$f\" -o \"{qc_out}/$bn\" --legacy hex dot; done"
            else:
                cmd = f"NanoPlot --fastq {qc_in} -o {qc_out} --legacy hex dot"
            st.session_state.pending_cmd = auto_fix_command(cmd)
        
        if st.button(t("btn_view_report"), use_container_width=True, key="btn_nanoplot_view"):
            st.session_state.show_report = True
            st.rerun()

    if st.button(t("clear_cmd"), key="btn_clear_sidebar"):
        st.session_state.pending_cmd = ""
        st.rerun()

# --- Main ---

st.title("microbiONT")

for msg in st.session_state.messages:
    css_class = "chat-user" if msg["role"] == "user" else "chat-ai"
    st.markdown(f'<div class="{css_class}">{msg["content"]}</div>', unsafe_allow_html=True)

if prompt := st.chat_input(t("chat_placeholder")):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.spinner(t("ai_thinking")):
        ctx = f"Settings: Pod5={st.session_state.get('s_d_in')}"
        resp = ask_ai(prompt, ctx)
        st.session_state.messages.append({"role": "assistant", "content": resp})
        has_cmd, extracted_cmd = parse_mixed_response(resp)
        if has_cmd: st.session_state.pending_cmd = auto_fix_command(extracted_cmd)
        st.rerun()

if st.session_state.pending_cmd and not st.session_state.is_executing:
    st.markdown("---")
    st.info(t("cmd_ready"))
    final_cmd = st.text_area("CMD", st.session_state.pending_cmd, height=100, label_visibility="collapsed")
    st.session_state.pending_cmd = final_cmd 
    c1, c2 = st.columns([1, 6])
    with c1:
        if st.button(t("btn_run"), type="primary", use_container_width=True, key="btn_exec_run"):
            st.session_state.is_executing = True
            st.rerun()
    with c2:
        if st.button(t("btn_cancel"), use_container_width=True, key="btn_exec_cancel"):
            st.session_state.pending_cmd = ""
            st.rerun()

if st.session_state.is_executing:
    try: run_command_logic(st.session_state.pending_cmd)
    except KeyboardInterrupt:
        st.session_state.messages.append({"role": "assistant", "content": t("status_stop")})
        st.session_state.is_executing = False
        st.rerun()

if st.session_state.get("show_report") and not st.session_state.is_executing:
    display_qc_report(st.session_state.nanoplot_output_dir, st.session_state.porechop_output_dir)

if st.session_state.last_log and not st.session_state.is_executing and not st.session_state.get("show_report"):
    st.markdown("---")
    with st.expander(t("log_title"), expanded=True):
        st.download_button(t("btn_download_log"), st.session_state.last_log, "log.txt", key="btn_dl_log")
        st.code(st.session_state.last_log, language="bash")
