import streamlit as st
from streamlit_option_menu import option_menu
import subprocess
import requests
import re
import os
import signal
import time
import glob
import shutil
import platform
import pandas as pd
from datetime import datetime
from PIL import Image

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

# ==========================================
# 1. Environment & Path Settings
# ==========================================

# Define the base directory of the app
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the 'bin' directory
BIN_DIR = os.path.join(BASE_DIR, "bin")

# Add 'bin' to the system PATH environment variable
os.environ["PATH"] = f"{BIN_DIR}:{os.environ.get('PATH', '')}"

# Attempt to grant execution permissions to binaries on Linux/macOS
try:
    if os.name == 'posix': 
        subprocess.run(f"chmod +x {BIN_DIR}/*", shell=True)
except Exception as e:
    pass

# Helper: Generate command prefix based on OS
def get_path_prefix():
    if platform.system() == "Darwin":
        return ""
    else:
        # For Linux/Windows, ensure the bin path is explicitly exported in commands
        bin_path = os.path.join(os.getcwd(), "bin")
        return f"export PATH={bin_path}:$PATH && "

# ==========================================
# 2. Session State Initialization (Data Warehouse)
# ==========================================

# Initialize the 'params' dictionary if it doesn't exist.
if "params" not in st.session_state:
    st.session_state.params = {
        # --- Tab 2: Dorado (Basecalling) ---
        "d_mod": "sup",
        "d_in": "pod5/",
        "d_out": "calls.bam",
        "d_out_fq": "calls.fastq",
        "d_duplex": False,
        "d_exe": "",

        # --- Tab 3: NanoFilt (Filtering) ---
        "n_in": "calls.fastq",
        "n_out": "filtered.fastq",
        "n_q": 15,          # User setting
        "n_l": 1450,
        "n_max": 1650,
        "do_pre": False,
        "do_post": False,

        # --- Tab 4: Porechop (Demultiplexing) ---
        "p_in": "filtered.fastq",
        "p_out": "porechop_out",
        "p_tr": 85,         # User setting
        "p_diff": 1,

        # --- Tab 5: QC Report ---
        "qc_in": "porechop_out/",
        "qc_out": "qc_report_final",
        "do_indiv": False,

        # --- Tab 6: Taxonomy Assignment (Emu) ---
        "tax_in": "porechop_out",    # Defaults to Porechop output
        "tax_out": "taxonomy_out",
        "tax_db": "",                # Will be auto-detected or selected
        "tax_threads": 8,
        "tax_sel_files": [],         # List of specific files selected by user

        # --- Tab 7: Format Conversion ---
        "cv_in": "taxonomy_out",  # Defaults to Emu output
        "cv_out": "conversion_out",
        "cv_db": "",                 # Synced from Tax DB
        "cv_do_ma": True,            # MicrobiomeAnalyst
        "cv_do_pi": False,           # PICRUSt2
        "cv_do_fa": False,           # FAPROTAX
                
        # --- Tab 8: Pipeline ---
        "pipe_start": "Basecalling",
        "pipe_stop": "Format Conversion",
        "pipe_skip_qc": False
    }

# ==========================================
# 3. Synchronization Callbacks
# ==========================================

def sync_dorado_to_nanofilt():
    if "params" in st.session_state:
        st.session_state.params["n_in"] = st.session_state.params["d_out_fq"]

def sync_nanofilt_to_porechop():
    if "params" in st.session_state:
        st.session_state.params["p_in"] = st.session_state.params["n_out"]

def sync_porechop_to_others():
    if "params" in st.session_state:
        out_dir = st.session_state.params["p_out"]
        st.session_state.params["qc_in"] = out_dir
        st.session_state.params["tax_in"] = out_dir

def sync_emu_to_conversion():
    if "params" in st.session_state:
        st.session_state.params["cv_in"] = st.session_state.params["tax_out"]

# ==========================================
# Global Configs
# ==========================================

OLLAMA_MODEL = "microbiONT" 
OLLAMA_URL = "http://localhost:11434/api/chat"
DORADO_MODELS = ["sup", "hac", "fast"]

TRANS = {
    "zh": {
        "sidebar_title": "microbiONT",
        "lang_select": "AI語言 (Language)",
        "chat_placeholder": "輸入對話或指令...",
        "ai_thinking": "microbiONT 正在思考...",
        "tab_home": "Home/About",
        "tab_flow": "One-Click Flow",
        "tab_dorado": "Basecalling",
        "tab_nanofilt": "Filtering",
        "tab_porechop": "Demultiplexing",
        "tab_nanoplot": "QC Report",
        "tab_emu": "Taxonomy",
        "tab_pipeline": "Custom Pipeline",
        "info_sop": "執行內建的標準分析流程 (SOP)",
        "btn_16s": "執行 16S 全流程 (含轉檔)",
        "btn_18s": "執行 18S 全流程 (含轉檔)",
        "model": "選擇模型 (Model)",
        "help_model": "選擇 Basecalling 模型：\n- sup: Super Accurate (最準確)\n- hac: High Accuracy (高準確)\n- fast: Fast (速度快)",
        "input_dir": "輸入資料夾 (Pod5)",
        "help_input_dir": "存放 .pod5 原始訊號檔的資料夾。",
        "output_file": "輸出檔案",
        "help_output_file": "設定輸出的檔名。",
        "output_fastq": "輸出 FASTQ 檔案 (.fastq)", 
        "help_output_fastq": "經 Samtools 轉換後，用於後續分析的序列檔名。",
        "chk_duplex": "啟用 Duplex (雙股校正)",
        "help_duplex": "開啟 Duplex 模式 (更準確)。",
        "dorado_exe": "Dorado 程式路徑",
        "help_dorado_exe": "若系統未設定環境變數，請在此輸入 dorado 執行檔的完整路徑。",
        "input_fastq": "輸入檔案 (.fastq)",
        "help_input_fastq": "要進行處理的 .fastq 序列檔案。",
        "output_dir": "輸出資料夾",
        "quality": "Q-Score 品質",
        "help_q": "過濾掉平均品質低於此數值的 Reads。",
        "min_len": "最小長度 (bp)",
        "help_min_len": "過濾掉長度短於此數值的 Reads。",
        "max_len": "最大長度 (bp)",
        "help_max_len": "過濾掉長度長於此數值的 Reads。",
        "chk_pre_qc": "Filter 前執行 QC",
        "help_pre_qc": "在過濾前先跑一次 QC 報告。",
        "chk_post_qc": "Filter 後執行 QC",
        "help_post_qc": "在過濾後再跑一次 QC 報告。",
        "help_out_dir": "輸出資料夾名稱。",
        "barcode_thresh": "Barcode 閾值 (%)",
        "help_thresh": "認定為該 Barcode 所需的序列匹配百分比。",
        "barcode_diff": "Barcode 差異值",
        "help_diff": "最佳匹配與次佳匹配的分數差異閾值。",
        "help_qc_in": "要進行 QC 的檔案或資料夾。",
        "chk_indiv_qc": "個別檔案 QC (迴圈模式)",
        "help_indiv_qc": "針對資料夾內的每個 .fastq 檔單獨產生一份 QC 報告。",
        "stats_title": "數據統計",
        "file_list_title": "檔案列表",
        "report_not_found": "找不到報告檔案。",
        "view_specific_bc": "選擇 Barcode",
        "emu_in_help": "輸入檔案 (通常是 Porechop 輸出的資料夾或檔案)",
        "tab_format": "格式轉換",
        "format_title": "格式轉換與視覺化",
        "pipeline_title": "客製化全流程",
        "home_title": "microbiONT: AI協助的Nanopore微生物分析平台",
        "home_desc": """
        專為 Oxford Nanopore Technologies (ONT) 定序數據設計，提供從原始訊號 (Pod5) 到 物種分類 (Taxonomy) 與常用文件格式轉換功能。
        
        整合工具包含：**Dorado, NanoFilt, Porechop, NanoPlot, Emu** 以及自動化格式轉換模組。
        
        **需要協助嗎？** 您可以隨時詢問內建的 **microbiONT AI**，它能協助您生成指令、排除疑難，並引導您順利完成分析流程。
        """,
        "usage_title": "功能特色與使用指南",
        "usage_content": """
        #### 1. 一鍵標準流程 (One-Click SOP)
        * **16S / 18S 全流程**：內建最佳化參數，自動執行 Basecalling → Filtering → Demultiplexing → QC → Taxonomy (Emu) → 轉檔。
        * **適用情境**：標準樣本分析，無需手動設定參數。

        #### 2. 客製化流程與獨立模組 (Custom Pipeline & Independent Modules)
        * **使用步驟 (Workflow)**：
          1. 請先前往各功能分頁 (Basecalling, Filtering 等) 設定所需參數。
          2. 點擊該分頁的 **Save Settings** 按鈕儲存設定。
          3. 最後前往 **Pipeline** 分頁，選擇流程起點與終點，系統將自動串接您儲存的參數。
        * **獨立使用 (Independent Use)**：每個分頁皆可單獨執行 (例如：只想跑 NanoPlot 或只跑 Emu)。
        * **功能特色**：支援彈性起訖點 (Start/Stop Step)、獨立轉檔功能 (Format Conversion)、以及個別檔案 QC。

        #### 3. 互動式終端機 (Interactive Terminal)
        * **AI 輔助**：在對話框輸入需求，AI 將自動生成指令。
        * **即時監控**：支援指令背景執行、即時查看 Log、並可隨時 **STOP** 中止程序。
        """,
        "citation_title": "引用文獻 (Citations)",
        "citation_content": """
        若您在研究中使用了本平台產生的結果，請引用以下工具 (依流程順序)：
        
        * **[Dorado]** (Basecalling):  
          Oxford Nanopore Technologies. "Dorado: high-performance basecaller." GitHub.
        
        * **[Samtools]** (FASTQ File Generation):  
          Li, H., et al. "The Sequence Alignment/Map format and SAMtools." *Bioinformatics* (2009).

        * **[NanoFilt]** (Filtering):  
          De Coster, W., et al. "NanoPack: visualizing and processing long-read sequencing data." *Bioinformatics* (2018).
        
        * **[Porechop]** (Demultiplexing):  
          Wick, R.R., et al. "Porechop: adapter trimmer for Oxford Nanopore reads." GitHub.
        
        * **[NanoPlot]** (Quality Control):  
          De Coster, W., et al. "NanoPlot: Creating quality control plots for long read sequencing data." *Bioinformatics* (2018).

        * **[Emu]** (Species-level taxonomy):  
          Curry, K.D., et al. "Emu: species-level microbial community profiling of full-length 16S rRNA Oxford Nanopore sequencing data." *Nature Methods* (2022).

        ...
        """,
        "context_prompt": "使用者介面語言為中文。請用中文回答說明，指令保持英文。",
        "unload_ai_msg": "正在卸載 AI 模型以釋放 VRAM...",
        "log_title": "執行紀錄 (Execution Log)",
        "status_success": "指令執行成功！",
        "status_fail": "指令執行失敗或被中斷。"
    },
    
    "en": {
        "sidebar_title": "microbiONT",
        "lang_select": "AI Language",
        "chat_placeholder": "Type message or command...",
        "ai_thinking": "microbiONT is thinking...",
        "tab_home": "Home / About",
        "tab_flow": "One-Click",
        "tab_dorado": "Basecalling",
        "tab_nanofilt": "Filtering",
        "tab_porechop": "Demultiplexing",
        "tab_nanoplot": "QC Report",
        "tab_emu": "Taxonomy",
        "tab_pipeline": "Pipeline",
        "info_sop": "Execute built-in Standard Operating Procedures (SOP).",
        "btn_16s": "Run 16S Workflow (Full)",
        "btn_18s": "Run 18S Workflow (Full)",
        "model": "Model",
        "help_model": "Select Basecalling model.",
        "input_dir": "Input Dir (Pod5)",
        "help_input_dir": "Directory containing .pod5 files.",
        "output_file": "Output File",
        "help_output_file": "Output filename.",
        "output_fastq": "Output FASTQ File",
        "help_output_fastq": "Converted .fastq filename for downstream analysis.",
        "chk_duplex": "Enable Duplex",
        "help_duplex": "Enable Duplex calling.",
        "dorado_exe": "Dorado Path",
        "help_dorado_exe": "Full path to dorado executable.",
        "input_fastq": "Input File",
        "help_input_fastq": "Input .fastq sequence file.",
        "output_dir": "Output Directory",
        "help_output_file": "Output filename.",
        "quality": "Quality (Q-Score)",
        "help_q": "Filter reads with average quality below this score.",
        "min_len": "Min Length (bp)",
        "help_min_len": "Filter reads shorter than this length.",
        "max_len": "Max Length (bp)",
        "help_max_len": "Filter reads longer than this length.",
        "chk_pre_qc": "Pre-QC",
        "help_pre_qc": "Run QC before filtering.",
        "chk_post_qc": "Post-QC",
        "help_post_qc": "Run QC after filtering.",
        "help_out_dir": "Output directory name.",
        "barcode_thresh": "Threshold (%)",
        "help_thresh": "Percentage of match required.",
        "barcode_diff": "Difference",
        "help_diff": "Score difference required.",
        "help_qc_in": "Input file or directory for QC.",
        "chk_indiv_qc": "Individual QC (Loop)",
        "help_indiv_qc": "Generate separate QC report for each file.",
        "stats_title": "Statistics",
        "file_list_title": "File List",
        "report_not_found": "Report not found.",
        "view_specific_bc": "Select Barcode",
        "emu_in_help": "Input file or directory (from Porechop)",
        "tab_format": "Format Conversion",
        "format_title": "Format Conversion & Visualization",
        "pipeline_title": "Custom Pipeline Builder", 
        "home_title": "microbiONT: AI-Driven Nanopore Analysis Platform",
        "home_desc": """
        Designed for Oxford Nanopore Technologies (ONT) sequencing data, offering a one-stop solution from raw signals (Pod5) to species taxonomy and formatting for downstream tools.
        
        Integrated tools: **Dorado, NanoFilt, Porechop, NanoPlot, Emu**, and automated format conversion modules.
        
        **Need assistance?** Just ask **microbiONT AI**! It can help you generate commands, troubleshoot issues, and guide you through the workflow.
        """,
        "usage_title": "Features & Guide",
        "usage_content": """
        #### 1. One-Click SOP
        * **Full 16S / 18S Workflow**: Automated execution of Basecalling → Filtering → Demultiplexing → QC → Taxonomy (Emu) → Format Conversion.
        * **Best for**: Standard analysis without manual tuning.

        #### 2. Custom Pipeline & Independent Modules
        * **Workflow**:
          1. Set parameters in individual tabs (Basecalling to Taxonomy).
          2. Click **Save Settings** in each tab.
          3. Go to **Pipeline** tab, select Start/Stop steps, and generate the workflow.
        * **Independent Use**: Each tab works standalone (e.g., run NanoPlot or Emu separately).
        * **Features**: Flexible Start/Stop points, standalone Format Conversion, and individual QC options.

        #### 3. Interactive Terminal
        * **AI-Assisted**: Type your request, and AI generates the bash command.
        * **Live Monitoring**: Background execution with live logs and **STOP** capability.
        """,
        "citation_title": "Citations",
        "citation_content": """
        Please cite the following tools if you use results from this platform (in workflow order):
        
        * **[Dorado]** (Basecalling):  
          Oxford Nanopore Technologies. "Dorado: high-performance basecaller." GitHub.
        
        * **[Samtools]** (FASTQ File Generation):  
          Li, H., et al. "The Sequence Alignment/Map format and SAMtools." *Bioinformatics* (2009).

        * **[NanoFilt]** (Filtering):  
          De Coster, W., et al. "NanoPack: visualizing and processing long-read sequencing data." *Bioinformatics* (2018).
        
        * **[Porechop]** (Demultiplexing):  
          Wick, R.R., et al. "Porechop: adapter trimmer for Oxford Nanopore reads." GitHub.
        
        * **[NanoPlot]** (Quality Control):  
          De Coster, W., et al. "NanoPlot: Creating quality control plots for long read sequencing data." *Bioinformatics* (2018).

        * **[Emu]** (Species-level taxonomy):  
          Curry, K.D., et al. "Emu: species-level microbial community profiling of full-length 16S rRNA Oxford Nanopore sequencing data." *Nature Methods* (2022).
        
        """,
        "context_prompt": "User interface language is English. Please reply in English.",
        "unload_ai_msg": "Unloading AI model to free up VRAM...",
        "log_title": "Execution Log",
        "status_success": "Command executed successfully.",
        "status_fail": "Command failed or was interrupted."
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
# 4. Helper Functions
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

def display_qc_report(qc_out_dir, porechop_dir, key_suffix=""):
    report_dir = qc_out_dir
    data_dir = porechop_dir
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
        bc_choice = st.selectbox(t("view_specific_bc"), subdirs, key=f"sel_bc_{key_suffix}")
        target = os.path.join(report_dir, bc_choice)
    
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
            
    with st.expander("Show All Plots"):
        sel = st.selectbox("Select Plot", sorted([os.path.basename(i) for i in imgs]), key=f"sel_plot_{key_suffix}")
        if sel: st.image(Image.open(os.path.join(target, sel)), caption=sel)

# ==========================================
# 5. UI Layout
# ==========================================

# --- sidebar ---
with st.sidebar:
    st.title(t("sidebar_title"))
    
    def update_language():
        selected = st.session_state.lang_radio_key
        if selected == "English":
            st.session_state.lang = "en"
        else:
            st.session_state.lang = "zh"

    st.radio(
        t("lang_select"), 
        ["English", "中文"], 
        horizontal=True, 
        index=0 if st.session_state.lang == "en" else 1,
        key="lang_radio_key",       
        on_change=update_language  
    )
    
    st.markdown("---")
    
# --- Sidebar Navigation ---
with st.sidebar:
    options_list = [
        "Home/About", 
        "One-Click Flow", 
        "Basecalling", 
        "Filtering", 
        "Demultiplexing", 
        "QC Report", 
        "Taxonomy", 
        "Format Conversion",
        "Custom Pipeline"
    ]
    
    icons_list = [
        "house",           # Home
        "hand-index",      # One-Click Flow
        "activity",        # Basecalling
        "funnel",          # Filtering
        "scissors",        # Demultiplexing
        "clipboard-data",  # QC report
        "list-columns-reverse", # Taxonomy
        "arrow-left-right",# Format convert
        "terminal"         # Custom Pipeline
    ]

    selected = option_menu(
        menu_title="MENU",  
        options=options_list,
        icons=icons_list,
        menu_icon="cast",      
        default_index=0,
        orientation="vertical", 
        styles={
            "container": {"padding": "8px", "background-color": "#fafafa"},
            "icon": {"color": "orange", "font-size": "20px"}, 
            "nav-link": {"font-size": "14px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": "#DAD8DA"},
        }
    )
    
    # [Page Content Logic]
    
    # [Page] Home / Citation
    if selected == "Home/About":
        st.subheader(t("home_title"))
        st.write(t("home_desc"))
        st.markdown("---")
        st.write(f"### {t('usage_title')}")
        st.markdown(t("usage_content"))
        st.markdown("---")
        st.write(f"### {t('citation_title')}")
        st.markdown(t("citation_content"))


# [Tab 1] One-Click Flow (Hardcoded SOP)
    elif selected == "One-Click Flow":
        st.info(t("info_sop"))
        
        base_dir = os.getcwd()
        bin_path = os.path.join(base_dir, "bin")
        emu_db_root = os.path.join(base_dir, "emu_db")
        
        exe_path = st.session_state.get("s_d_exe", "").strip()
        dorado_cmd = exe_path if exe_path else "dorado"
        p5_in = st.session_state.get("s_d_in", "pod5/")
        pc_out = st.session_state.get("s_p_out", "porechop_out")
        qc_out = st.session_state.get("nanoplot_output_dir", "qc_report_final")
        emu_out = "taxonomy_out"

        # 16S and 18S button
        c1, c2 = st.columns(2)
        
        # --- 16S workflow ---
        with c1:
            st.caption("For 16S Full Flow (Basecalling -> Taxonomy -> Conversion)")
            if st.button(t("btn_16s"), use_container_width=True, key="btn_flow_16s"):
                # 16S 
                q_val, min_l, max_l = 15, 1450, 1650
                db_name = "16S_NCBI"
                db_path = os.path.join(emu_db_root, db_name)
                
                if not os.path.exists(db_path):
                      st.error(f"❌ Database not found: {db_path}\nPlease check if folder '{db_name}' exists in 'emu_db'.")
                else:
                    cmds = []
                    prefix = get_path_prefix()
                    if prefix: 
                        cmds.append(prefix.replace(" && ", ""))
                    cmds.append(f"{dorado_cmd} basecaller sup {p5_in} > calls.bam && samtools fastq calls.bam > calls.fastq")
                    cmds.append(f"cat calls.fastq | NanoFilt -q {q_val} -l {min_l} --maxlength {max_l} --readtype 1D > filtered.fastq")
                    cmds.append(f"porechop -i filtered.fastq -b {pc_out} --barcode_threshold 85 --barcode_diff 1")
                    cmds.append(f"NanoPlot --fastq {pc_out}/*.fastq -o {qc_out} --legacy hex dot")
                    cmds.append(f"mkdir -p {emu_out}")
                    loop_cmd = f"for f in \"{pc_out}\"/*.fastq; do if [ -f \"$f\" ]; then emu abundance --type map-ont --db {db_path} --keep-counts \"$f\" --output-dir {emu_out}; fi; done"
                    cmds.append(loop_cmd)
                    # ✅ FIXED: Reverted to tax_id --counts
                    cmds.append(f"emu combine-outputs \"{emu_out}\" tax_id --counts") 
                    cmds.append(f"echo 'Starting Post-Processing...' && python3 post_process.py -i {emu_out} -o conversion_out -d {db_path} --ma")
                    
                    full_cmd = " && ".join(cmds)
                    st.session_state.messages.append({"role": "assistant", "type": "text", "content": f"**16S Full Pipeline Started**\nDatabase: `{db_name}`"})
                    st.session_state.messages.append({"role": "assistant", "type": "terminal", "content": auto_fix_command(full_cmd)})
                    st.rerun()

        with c2:
            st.caption("For 18S Full Flow (Basecalling -> Taxonomy -> Conversion)")
            if st.button(t("btn_18s"), use_container_width=True, key="btn_flow_18s"):
                
                q_val, min_l, max_l = 15, 1800, 1950
                db_name = "18S_C_P_P"
                db_path = os.path.join(emu_db_root, db_name)
                
                if not os.path.exists(db_path):
                      st.error(f"❌ Database not found: {db_path}\nPlease check if folder '{db_name}' exists in 'emu_db'.")
                else:
                    cmds = []
                    cmds.append(f"export PATH={bin_path}:$PATH")
                    cmds.append(f"{dorado_cmd} basecaller sup {p5_in} > calls.bam && samtools fastq calls.bam > calls.fastq")
                    cmds.append(f"cat calls.fastq | NanoFilt -q {q_val} -l {min_l} --maxlength {max_l} --readtype 1D > filtered.fastq")
                    cmds.append(f"porechop -i filtered.fastq -b {pc_out} --barcode_threshold 85 --barcode_diff 1")
                    cmds.append(f"NanoPlot --fastq {pc_out}/*.fastq -o {qc_out} --legacy hex dot")
                    cmds.append(f"mkdir -p {emu_out}")
                    loop_cmd = f"for f in \"{pc_out}\"/*.fastq; do if [ -f \"$f\" ]; then emu abundance --type map-ont --db {db_path} --keep-counts \"$f\" --output-dir {emu_out}; fi; done"
                    cmds.append(loop_cmd)
                    # ✅ FIXED: Reverted to tax_id --counts
                    cmds.append(f"emu combine-outputs \"{emu_out}\" tax_id --counts") 
                    cmds.append(f"echo 'Starting Post-Processing...' && python3 post_process.py -i {emu_out} -o conversion_out -d {db_path} --ma")
                    
                    full_cmd = " && ".join(cmds)
                    st.session_state.messages.append({"role": "assistant", "type": "text", "content": f"**18S Full Pipeline Started**\nDatabase: `{db_name}`"})
                    st.session_state.messages.append({"role": "assistant", "type": "terminal", "content": auto_fix_command(full_cmd)})
                    st.rerun()

        st.write("") 
        st.write("") 
        
        st.markdown("""
        ---
        **Note:**
        The default workflows above are optimized for **Full-Length 16S and 18S** analysis. 
        
        If you need to change parameters or steps (e.g., custom database, different Q-score), please:
        1. Set the parameters form **Basecalling to Taxonomy** tab, then use the **Pipeline** tab for a custom workflow builder.
        2. Or edit the generated command directly in the **Terminal** window below before clicking RUN.
        3. Type requirements in the chat box below, AI assistant will help you.
        """)

# --- [Tab 2 ] Dorado (Basecalling) ---
    elif selected == "Basecalling":
        
        if "params" not in st.session_state:
            st.session_state.params = {
                "d_mod": "sup", "d_in": "pod5/", "d_out": "calls.bam",
                "d_out_fq": "calls.fastq", "d_duplex": False, "d_exe": ""
            }
        p = st.session_state.params 
        st.header("Basecalling Settings (Dorado)") 

        # 1. Model Selection
        current_mod = st.selectbox(
            t("model"), 
            ["sup", "hac", "fast"], 
            index=["sup", "hac", "fast"].index(p["d_mod"]) if p["d_mod"] in ["sup", "hac", "fast"] else 0,
            help=t("help_model")
        )
        if current_mod != p["d_mod"]:
            st.session_state.params["d_mod"] = current_mod
            st.rerun()

        # 2. Input Directory
        new_in = st.text_input(t("input_dir"), value=p["d_in"], help=t("help_input_dir"))
        if new_in != p["d_in"]:
            st.session_state.params["d_in"] = new_in

        # 3. Output BAM
        new_out = st.text_input(t("output_file"), value=p["d_out"], help=t("help_output_file"))
        if new_out != p["d_out"]:
            st.session_state.params["d_out"] = new_out

        # 4. Output FASTQ
        def update_fq():
            st.session_state.params["d_out_fq"] = st.session_state._temp_fq
            sync_dorado_to_nanofilt()

        st.text_input(
            t("output_fastq"), 
            value=p["d_out_fq"], 
            key="_temp_fq", 
            on_change=update_fq,
            help=t("help_output_fastq")
        )

        with st.expander("Advanced Options"):
            # Duplex
            new_duplex = st.checkbox(t("chk_duplex"), value=p["d_duplex"], help=t("help_duplex"))
            if new_duplex != p["d_duplex"]:
                st.session_state.params["d_duplex"] = new_duplex

            # Exe Path
            new_exe = st.text_input(
                t("dorado_exe"), 
                value=p["d_exe"], 
                placeholder="/path/to/dorado", 
                help=t("help_dorado_exe")
            )
            if new_exe != p["d_exe"]:
                st.session_state.params["d_exe"] = new_exe

        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            st.caption("For final custom pipeline")
            if st.button("Save Settings", use_container_width=True, key="confirm_tab2"):
                st.toast("✅ Basecalling Settings Saved!")
        
        with c2:
            st.caption("For only Basecalling")
            if st.button("Generate Command", use_container_width=True, key="btn_dorado_gen"):
                exe = p["d_exe"].strip() if p["d_exe"].strip() else "dorado"
                
                cmd_part1 = f"{exe} basecaller {p['d_mod']} {p['d_in']} > {p['d_out']}"
                if p["d_duplex"]:
                    cmd_part1 = f"{exe} basecaller {p['d_mod']} {p['d_in']} --emit-fastq > {p['d_out']}" 
                cmd_part2 = f"samtools fastq {p['d_out']} > {p['d_out_fq']}"
                
                full_cmd = f"{cmd_part1} && {cmd_part2}"
                
                st.session_state.messages.append({"role": "assistant", "type": "terminal", "content": auto_fix_command(full_cmd)})
                st.rerun()
            
# --- [Tab 3] NanoFilt (Filtering) ---
    elif selected == "Filtering":
        p = st.session_state.params 
        
        st.header("Filtering Settings (NanoFilt)")

        # 1. Input FASTQ 
        new_n_in = st.text_input(t("input_fastq"), value=p["n_in"], help=t("help_input_fastq"))
        if new_n_in != p["n_in"]:
            st.session_state.params["n_in"] = new_n_in

        # 2. Output FASTQ 
        new_n_out = st.text_input(t("output_file"), value=p["n_out"], help=t("help_output_file"))
        if new_n_out != p["n_out"]:
            st.session_state.params["n_out"] = new_n_out
            sync_nanofilt_to_porechop() 

        # 3. Quality Slider
        new_n_q = st.slider(t("quality"), 5, 30, value=p["n_q"], help=t("help_q"))
        if new_n_q != p["n_q"]: st.session_state.params["n_q"] = new_n_q
        
        # 4. Length Filters
        c1, c2 = st.columns(2)
        with c1: 
            new_n_l = st.number_input(t("min_len"), 0, 10000, value=p["n_l"], help=t("help_min_len"))
            if new_n_l != p["n_l"]: st.session_state.params["n_l"] = new_n_l
        with c2: 
            new_n_max = st.number_input(t("max_len"), 0, 10000, value=p["n_max"], help=t("help_max_len"))
            if new_n_max != p["n_max"]: st.session_state.params["n_max"] = new_n_max
        
        # 5. QC Options & Reports
        c_pre1, c_pre2 = st.columns([2, 1])
        with c_pre1:
            new_do_pre = st.checkbox(t("chk_pre_qc"), value=p["do_pre"], help=t("help_pre_qc"))
            if new_do_pre != p["do_pre"]: st.session_state.params["do_pre"] = new_do_pre
        with c_pre2:
            if st.button("View Pre-QC Report", use_container_width=True, key="btn_view_pre_qc"):
                pre_dir = f"{os.path.splitext(p['n_in'])[0]}_pre_qc"
                st.session_state.messages.append({
                    "role": "assistant", 
                    "type": "report", 
                    "content": f"Pre-QC Analysis ({pre_dir})",
                    "qc_dir": pre_dir
                })
                st.rerun()

        c_post1, c_post2 = st.columns([2, 1])
        with c_post1:
            new_do_post = st.checkbox(t("chk_post_qc"), value=p["do_post"], help=t("help_post_qc"))
            if new_do_post != p["do_post"]: st.session_state.params["do_post"] = new_do_post
        with c_post2:
            if st.button("View Post-QC Report", use_container_width=True, key="btn_view_post_qc"):
                post_dir = f"{os.path.splitext(p['n_out'])[0]}_post_qc"
                st.session_state.messages.append({
                    "role": "assistant", 
                    "type": "report", 
                    "content": f"Post-QC Analysis ({post_dir})",
                    "qc_dir": post_dir
                })
                st.rerun()
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            st.caption("For final custom pipeline")
            if st.button("Save Settings", use_container_width=True, key="confirm_tab3"):
                st.toast("✅ Filter Settings Saved! Please go to [Demultiplex] tab.")
        
        with c2:
            st.caption("For only Filtering")
            if st.button("Generate Command", use_container_width=True, key="btn_nanofilt_gen"):
                cmds = []
                if p["do_pre"]: cmds.append(f"NanoPlot --fastq {p['n_in']} -o {os.path.splitext(p['n_in'])[0]}_pre_qc --legacy hex dot")
                cmds.append(f"cat {p['n_in']} | NanoFilt -q {p['n_q']} -l {p['n_l']} --maxlength {p['n_max']} --readtype 1D > {p['n_out']}")
                if p["do_post"]: cmds.append(f"NanoPlot --fastq {p['n_out']} -o {os.path.splitext(p['n_out'])[0]}_post_qc --legacy hex dot")
                
                st.session_state.messages.append({"role": "assistant", "type": "terminal", "content": auto_fix_command(" && ".join(cmds))})
                st.rerun()
                
    # --- [Tab 4] Porechop (Demultiplexing) ---
    elif selected == "Demultiplexing":
        p = st.session_state.params
        st.header("Demultiplexing (Porechop)")
        
        # 1. Input FASTQ
        new_p_in = st.text_input(t("input_fastq"), value=p["p_in"], help=t("help_input_fastq"))
        if new_p_in != p["p_in"]: st.session_state.params["p_in"] = new_p_in

        # 2. Output Dir 
        new_p_out = st.text_input(t("output_dir"), value=p["p_out"], help=t("help_out_dir"))
        if new_p_out != p["p_out"]:
            st.session_state.params["p_out"] = new_p_out
            sync_porechop_to_others() 

        # 3. Parameters
        new_p_tr = st.slider(t("barcode_thresh"), 0, 100, value=p["p_tr"], help=t("help_thresh"))
        if new_p_tr != p["p_tr"]: st.session_state.params["p_tr"] = new_p_tr

        new_p_diff = st.number_input(t("barcode_diff"), 0, 10, value=p["p_diff"], help=t("help_diff"))
        if new_p_diff != p["p_diff"]: st.session_state.params["p_diff"] = new_p_diff
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            st.caption("For final custom pipeline")
            if st.button("Save Settings", use_container_width=True, key="confirm_tab4"):
                st.toast("✅ Porechop Settings Saved! Please go to [QC Report] tab.")
        
        with c2:
            st.caption("For only Demultiplexing")
            if st.button("Generate Command", use_container_width=True, key="btn_porechop_gen"):
                cmd = f"porechop -i {p['p_in']} -b {p['p_out']} --barcode_threshold {p['p_tr']} --barcode_diff {p['p_diff']}"
                st.session_state.messages.append({"role": "assistant", "type": "terminal", "content": auto_fix_command(cmd)})
                st.rerun()

    # --- [Tab 5] NanoPlot (QC Report) ---
    elif selected == "QC Report":
        p = st.session_state.params
        st.header("Quality Control (NanoPlot)")

        # 1. Inputs
        new_qc_in = st.text_input("Input", value=p["qc_in"], help=t("help_qc_in"))
        if new_qc_in != p["qc_in"]: st.session_state.params["qc_in"] = new_qc_in

        new_qc_out = st.text_input("Output Report", value=p["qc_out"], help=t("help_out_dir"))
        if new_qc_out != p["qc_out"]: st.session_state.params["qc_out"] = new_qc_out

        new_indiv = st.checkbox(t("chk_indiv_qc"), value=p["do_indiv"], help=t("help_indiv_qc"))
        if new_indiv != p["do_indiv"]: st.session_state.params["do_indiv"] = new_indiv
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            st.caption("For final custom pipeline")
            if st.button("Save Settings", use_container_width=True, key="confirm_tab5"):
                st.toast("✅ QC Settings Saved!")

        with c2:
            st.caption("For only QC Generation")
            if st.button("Generate Command", use_container_width=True, key="btn_nanoplot_gen"):
                if p["do_indiv"]:
                    src = p["qc_in"].rstrip("/")
                    pat = os.path.join(src, "*.fastq") if not src.endswith("q") else src
                    cmd = f"mkdir -p {p['qc_out']} && for f in {pat}; do bn=$(basename \"$f\" .fastq); NanoPlot --fastq \"$f\" -o \"{p['qc_out']}/$bn\" --legacy hex dot; done"
                else:
                    cmd = f"NanoPlot --fastq {p['qc_in']} -o {p['qc_out']} --legacy hex dot"
                
                st.session_state.messages.append({"role": "assistant", "type": "terminal", "content": auto_fix_command(cmd)})
                st.rerun()
        
        st.markdown("---")
        if st.button("📄 View Generated Report", use_container_width=True, key="btn_nanoplot_view"):
            st.session_state.messages.append({
                "role": "assistant", 
                "type": "report", 
                "content": p["qc_out"],
                "qc_dir": p["qc_out"],
                "pc_dir": p["p_out"]
            })
            st.rerun()
# ==========================================
    # [Tab 6] Emu (Taxonomy)
    # ==========================================
    elif selected == "Taxonomy":
        p = st.session_state.params
        st.header("Taxonomy Assignment (Emu)")

        # 1. Input Directory (Synced from Porechop)
        new_tax_in = st.text_input(t("input_fastq"), value=p["tax_in"], help=t("emu_in_help"))
        if new_tax_in != p["tax_in"]: st.session_state.params["tax_in"] = new_tax_in
        
# File Selection Logic (Multiselect)
        selected_files_val = []
        if os.path.exists(p["tax_in"]) and os.path.isdir(p["tax_in"]):
            try:
                all_fastqs = sorted([f for f in os.listdir(p["tax_in"]) if f.endswith(".fastq")])
                if all_fastqs:
                    # Update stored selection to only include valid files
                    valid_defaults = [f for f in p["tax_sel_files"] if f in all_fastqs]
                    
                    selected_files_val = st.multiselect(
                        f"Select files ({len(all_fastqs)} found)", 
                        all_fastqs, 
                        default=valid_defaults,
                        help="Select specific files.",
                        key="tax_real_files_select"  
                    )
                    # Update params if selection changed
                    if selected_files_val != p["tax_sel_files"]:
                        st.session_state.params["tax_sel_files"] = selected_files_val
            except Exception:
                pass
        else:
            # Virtual barcodes for offline/template mode
            virtual_barcodes = [f"BC{str(i).zfill(2)}.fastq" for i in range(1, 97)]
            
            valid_defaults = [f for f in p["tax_sel_files"] if f in virtual_barcodes]
            
            selected_files_val = st.multiselect(
                "Pre-select Barcodes", 
                virtual_barcodes, 
                default=valid_defaults,
                key="tax_virtual_bc_select" 
            )
            
            if selected_files_val != p["tax_sel_files"]:
                st.session_state.params["tax_sel_files"] = selected_files_val
        # 2. Output Directory (Syncs to Tab 7)
        new_tax_out = st.text_input(t("output_dir"), value=p["tax_out"], help=t("help_out_dir"))
        if new_tax_out != p["tax_out"]:
            st.session_state.params["tax_out"] = new_tax_out
            sync_emu_to_conversion() # Trigger sync

        st.markdown("---")
        
        # 3. Database Selection
        db_root = os.path.join(os.getcwd(), "emu_db")
        db_options = []
        if os.path.exists(db_root):
            db_options = sorted([d for d in os.listdir(db_root) if os.path.isdir(os.path.join(db_root, d)) and not d.startswith(".")])
        else:
            st.warning(f"⚠️ Database folder not found: {db_root}")

        # Determine index for selectbox
        PREFERRED_DB = "16S_NCBI"
        current_db = p["tax_db"]
        
        # If current param is empty, try to set default
        if not current_db and PREFERRED_DB in db_options:
            current_db = PREFERRED_DB
        
        idx = db_options.index(current_db) if current_db in db_options else 0
        
        new_db = st.selectbox("Select Database", db_options, index=idx if db_options else 0, help="Select a database.")
        
        if new_db != p["tax_db"]:
            st.session_state.params["tax_db"] = new_db
            # Auto-sync to Conversion DB as well
            st.session_state.params["cv_db"] = new_db

        final_db_path = os.path.join(db_root, p["tax_db"]) if p["tax_db"] else db_root

        st.markdown("---")
        
        # 4. Buttons
        c1, c2 = st.columns(2)
        with c1:
             st.caption("For final pipeline")
             if st.button("Save Settings", use_container_width=True, key="confirm_tab6"):
                st.toast("✅ Emu Settings Saved!")
                
        with c2:
            st.caption("For only Taxonomy")
            if st.button("Generate Command", use_container_width=True, key="btn_emu_gen"):
                files_str = " ".join([f"\"{os.path.join(p['tax_in'], f)}\"" for f in p["tax_sel_files"]]) if p["tax_sel_files"] else f"\"{p['tax_in']}\"/*.fastq"
                
                prefix = get_path_prefix()
                cmd = f"{prefix}mkdir -p {p['tax_out']} && "
                cmd += f"for f in {files_str}; do "
                cmd += f"bn=$(basename \"$f\" .fastq); "
                cmd += f"if [ -f \"$f\" ]; then emu abundance --type map-ont --db {final_db_path} --keep-counts \"$f\" --output-dir {p['tax_out']}; fi; done && "
                # ✅ FIXED: Reverted to tax_id --counts
                cmd += f"emu combine-outputs \"{p['tax_out']}\" tax_id --counts"
                
                st.session_state.messages.append({"role": "assistant", "type": "terminal", "content": auto_fix_command(cmd)})
                st.rerun()

    # ==========================================
    # [Tab 7] Format Conversion
    # ==========================================
    elif selected == "Format Conversion":
        p = st.session_state.params
        st.info("Convert Emu results into formats compatible with MicrobiomeAnalyst, PICRUSt2, and FAPROTAX.")
    
        # 1. I/O Settings
        st.write("###### Input / Output Settings")
        c1, c2 = st.columns(2)
        
        with c1:
            # Synced from Emu
            new_cv_in = st.text_input("Input Directory (taxonomy_out)", value=p["cv_in"], help="Input directory from taxonomy_out")
            if new_cv_in != p["cv_in"]: st.session_state.params["cv_in"] = new_cv_in

        with c2:
            # Auto-suggest output name based on input
            default_out = f"{p['cv_in']}_converted" if p["cv_in"] else "taxonomy_out_converted"
            # If user hasn't manually set cv_out (or it's empty), update it
            val_to_show = p["cv_out"] if p["cv_out"] else default_out
            
            new_cv_out = st.text_input("Output Directory", value=val_to_show, help=t("help_out_dir"))
            if new_cv_out != p["cv_out"]: st.session_state.params["cv_out"] = new_cv_out

        st.markdown("---")

        # 2. Database Settings (Synced from Emu)
        st.write("###### Database Settings")
        db_root = os.path.join(os.getcwd(), "emu_db")
        db_options = []
        if os.path.exists(db_root):
            db_options = sorted([d for d in os.listdir(db_root) if os.path.isdir(os.path.join(db_root, d)) and not d.startswith(".")])

        # Logic to keep selection persistent
        curr_cv_db = p["cv_db"]
        idx_cv = db_options.index(curr_cv_db) if curr_cv_db in db_options else 0
        
        new_cv_db = st.selectbox("Select Database", db_options, index=idx_cv, key="sel_cv_db")
        if new_cv_db != p["cv_db"]: st.session_state.params["cv_db"] = new_cv_db
        
        final_cv_db_path = os.path.join(db_root, p["cv_db"]) if p["cv_db"] else db_root

        st.markdown("---")

        # 3. Output Formats (Persistent Checkboxes)
        st.write("###### Output Formats")
        st.caption("Select output formats to convert results for compatibility with downstream analysis tools")
        c1, c2, c3 = st.columns(3)
        
        new_ma = c1.checkbox("MicrobiomeAnalyst", value=p["cv_do_ma"])
        if new_ma != p["cv_do_ma"]: st.session_state.params["cv_do_ma"] = new_ma
        
        new_pi = c2.checkbox("PICRUSt2", value=p["cv_do_pi"])
        if new_pi != p["cv_do_pi"]: st.session_state.params["cv_do_pi"] = new_pi
        
        new_fa = c3.checkbox("FAPROTAX", value=p["cv_do_fa"])
        if new_fa != p["cv_do_fa"]: st.session_state.params["cv_do_fa"] = new_fa

        st.markdown("---")

        # 4. Action Buttons
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Save Settings", use_container_width=True, key="btn_save_tab7"):
                st.toast("✅ Format Conversion settings saved!")

        with b2:
            if st.button("Generate Command", type="primary", use_container_width=True, key="btn_gen_tab7"):
                if not os.path.exists(p["cv_in"]):
                    st.error(f"❌ Input directory not found: {p['cv_in']}")
                elif not os.path.exists(final_cv_db_path):
                    st.error(f"❌ Database path not found: {final_cv_db_path}")
                else:
                    py_args = f"-i {p['cv_in']} -o {p['cv_out']} -d {final_cv_db_path}"
                    if p["cv_do_ma"]: py_args += " --ma"
                    if p["cv_do_pi"]: py_args += " --picrust"
                    if p["cv_do_fa"]: py_args += " --faprotax"
                    
                    cmd = f"mkdir -p {p['cv_out']} && python3 post_process.py {py_args}"
                    st.session_state.messages.append({"role": "assistant", "type": "terminal", "content": auto_fix_command(cmd)})
                    st.rerun()

    # ==========================================
    # [Tab 8] Pipeline Run
    # ==========================================
    elif selected == "Custom Pipeline":
        p = st.session_state.params # Retrieve warehouse
        
        # 1. Step Definitions
        STEP_ORDER = [
            "Basecalling", 
            "Filtering", 
            "Demultiplexing", 
            "QC Report", 
            "Taxonomy", 
            "Format Conversion"
        ]
        
        # 2. UI Selection (Persistent)
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            start_idx = STEP_ORDER.index(p["pipe_start"]) if p["pipe_start"] in STEP_ORDER else 0
            new_start = st.selectbox("Start Step", STEP_ORDER, index=start_idx)
            if new_start != p["pipe_start"]: st.session_state.params["pipe_start"] = new_start
            
        with c2:
            # Filter valid stop steps based on current start
            valid_stops = STEP_ORDER[STEP_ORDER.index(p["pipe_start"]):]
            current_stop = p["pipe_stop"] if p["pipe_stop"] in valid_stops else valid_stops[-1]
            
            new_stop = st.selectbox("Stop Step", valid_stops, index=valid_stops.index(current_stop))
            if new_stop != p["pipe_stop"]: st.session_state.params["pipe_stop"] = new_stop
            
        with c3:
            st.write("") 
            st.write("") 
            new_skip = st.checkbox("Skip QC", value=p["pipe_skip_qc"], help="Check this to skip QC generation.")
            if new_skip != p["pipe_skip_qc"]: st.session_state.params["pipe_skip_qc"] = new_skip

        # Calculate logical flags based on current selection
        s_idx = STEP_ORDER.index(p["pipe_start"])
        e_idx = STEP_ORDER.index(p["pipe_stop"])
        
        run_dorado      = (0 >= s_idx and 0 <= e_idx)
        run_filter      = (1 >= s_idx and 1 <= e_idx)
        run_porechop    = (2 >= s_idx and 2 <= e_idx)
        qc_in_range     = (3 >= s_idx and 3 <= e_idx)
        run_qc          = qc_in_range and not p["pipe_skip_qc"]
        run_emu         = (4 >= s_idx and 4 <= e_idx)
        run_conversion  = (5 >= s_idx and 5 <= e_idx)
        
        # Display Current Plan
        steps_to_run = []
        if run_dorado: steps_to_run.append("Basecalling")
        if run_filter: steps_to_run.append("Filtering")
        if run_porechop: steps_to_run.append("Demultiplexing")
        if run_qc: 
            qc_type = "(Individual)" if p["do_indiv"] else "(Combined)"
            steps_to_run.append(f"QC Report {qc_type}")
        if run_emu: steps_to_run.append("Taxonomy")
        if run_conversion: steps_to_run.append("Format Conversion")
        
        if not steps_to_run:
            st.warning("⚠️ No steps selected.")
        else:
            st.info(f"📋 Current Plan: {' → '.join(steps_to_run)}")

        st.markdown("---")

        # Buttons
        c1, c2 = st.columns(2)
        with c1:
             st.caption("Save settings for future runs")
             if st.button("Save Settings", use_container_width=True, key="confirm_tab8"):
                st.toast("✅ Pipeline Settings Saved!")
        
        with c2:
            st.caption("Execute Selected Range")
            if st.button("Generate Command", type="primary", use_container_width=True, key="btn_gen_pipe_cmd"):
                cmds = []
                last_output_fastq = "" 
                last_output_dir = "" 
                prefix = get_path_prefix()

                # 1. Dorado (Reading from Params)
                if run_dorado:
                    exe = p["d_exe"].strip() or "dorado"
                    step1 = f"{prefix}{exe} basecaller {p['d_mod']} {p['d_in']} > {p['d_out']} && samtools fastq {p['d_out']} > {p['d_out_fq']}"
                    cmds.append(step1)
                    
                    last_output_fastq = p["d_out_fq"]
                    last_output_dir = os.path.dirname(p["d_out_fq"]) or "."
                else:
                    # If skipping Dorado, pick up from NanoFilt input
                    last_output_fastq = p["n_in"]
                    last_output_dir = "."

                # 2. Filter (Reading from Params)
                if run_filter:
                    if p["do_pre"]:
                        pre_qc_dir = f"{os.path.splitext(last_output_fastq)[0]}_pre_qc"
                        cmds.append(f"NanoPlot --fastq {last_output_fastq} -o {pre_qc_dir} --legacy hex dot")

                    step2 = f"cat {last_output_fastq} | NanoFilt -q {p['n_q']} -l {p['n_l']} --maxlength {p['n_max']} --readtype 1D > {p['n_out']}"
                    cmds.append(step2)
                    
                    last_output_fastq = p["n_out"]
                    last_output_dir = os.path.dirname(p["n_out"]) or "."
                    
                    if p["do_post"]:
                        post_qc_dir = f"{os.path.splitext(p['n_out'])[0]}_post_qc"
                        cmds.append(f"NanoPlot --fastq {p['n_out']} -o {post_qc_dir} --legacy hex dot")
                else:
                    # If skipping Filter, pick up from Porechop input
                    if run_porechop: 
                        last_output_fastq = p["p_in"]

                # 3. Porechop (Reading from Params)
                if run_porechop:
                    step3 = f"porechop -i {last_output_fastq} -b {p['p_out']} --barcode_threshold {p['p_tr']} --barcode_diff {p['p_diff']}"
                    cmds.append(step3)
                    last_output_dir = p["p_out"]
                else:
                    if not run_dorado and not run_filter:
                          # If starting mid-way, check if we start at Taxonomy or QC
                          pass

                # 4. NanoPlot (Reading from Params)
                if run_qc:
                    # Logic: If Porechop ran OR we have a directory as input -> wildcard
                    is_dir_source = False
                    if run_porechop or (os.path.isdir(last_output_dir) and last_output_dir != "."):
                         qc_target = f"{last_output_dir}/*.fastq"
                         is_dir_source = True
                    else:
                         qc_target = last_output_fastq
                         is_dir_source = False
                    
                    if p["do_indiv"] and is_dir_source:
                        step4 = f"mkdir -p {p['qc_out']} && "
                        step4 += f"for f in {qc_target}; do bn=$(basename \"$f\" .fastq); NanoPlot --fastq \"$f\" -o \"{p['qc_out']}/$bn\" --legacy hex dot; done"
                    else:
                        step4 = f"NanoPlot --fastq {qc_target} -o {p['qc_out']} --legacy hex dot"
                    
                    cmds.append(step4)

                # 5. Emu (Reading from Params)
                if run_emu:
                    # Logic Fix for Emu Input
                    if run_porechop:
                        # Case A: Porechop ran, so input is definitely a directory
                        emu_in = last_output_dir
                        is_input_dir = True
                    else:
                        # Case B: Porechop didn't run. Are we starting AT Taxonomy?
                        if p["pipe_start"] == "Taxonomy":
                             emu_in = p["tax_in"]
                             # Rough check if it looks like a file or dir based on extension
                             is_input_dir = not (emu_in.endswith(".fastq") or emu_in.endswith(".fq"))
                        else:
                             # Case C: Coming from Filter or Basecalling (Single File)
                             emu_in = last_output_fastq
                             is_input_dir = False

                    final_emu_out = p["tax_out"]
                    
                    # Database path resolution
                    final_db_path = p["tax_db"] if p["tax_db"] else "16S_NCBI"
                    if "emu_db" not in final_db_path and not os.path.isabs(final_db_path):
                         final_db_path = os.path.join(os.getcwd(), "emu_db", final_db_path)

                    if is_input_dir:
                        # Use params['tax_sel_files']
                        sel_files = p["tax_sel_files"]
                        target_loop = " ".join([f"\"{os.path.join(emu_in, f)}\"" for f in sel_files]) if sel_files else f"\"{emu_in}\"/*.fastq"
                        loop_cmd = f"for f in {target_loop}; do bn=$(basename \"$f\" .fastq); if [ -f \"$f\" ]; then emu abundance --type map-ont --db {final_db_path} --keep-counts \"$f\" --output-dir {final_emu_out}; fi; done"
                    else:
                        loop_cmd = f"emu abundance --type map-ont --db {final_db_path} --keep-counts \"{emu_in}\" --output-dir {final_emu_out}"

                    # ✅ FIXED: Reverted to tax_id --counts
                    step5 = f"{prefix}mkdir -p {final_emu_out} && {loop_cmd} && emu combine-outputs \"{final_emu_out}\" tax_id --counts" 
                    cmds.append(step5)

                # 6. Format Conversion (Reading from Params)
                if run_conversion:
                    # Ensure DB matches
                    conv_db_path = p["cv_db"] if p["cv_db"] else p["tax_db"]
                    if not conv_db_path: conv_db_path = "16S_NCBI"
                    
                    if "emu_db" not in conv_db_path and not os.path.isabs(conv_db_path):
                         conv_db_path = os.path.join(os.getcwd(), "emu_db", conv_db_path)

                    if any([p["cv_do_ma"], p["cv_do_pi"], p["cv_do_fa"], p["cv_do_tr"]]):
                        py_args = f"-i {p['tax_out']} -o {p['cv_out']} -d {conv_db_path}"
                        if p["cv_do_ma"]: py_args += " --ma"
                        if p["cv_do_pi"]: py_args += " --picrust"
                        if p["cv_do_fa"]: py_args += " --faprotax"
                        
                        cmds.append(f"echo 'Starting Post-Processing...' && python3 post_process.py {py_args}")

                full_pipeline_cmd = " && ".join(cmds)
                
                st.session_state.messages.append({"role": "assistant", "type": "terminal", "content": auto_fix_command(full_pipeline_cmd)})
                st.rerun()
                
# ==========================================
# Main Area: Conversational UI (Bubble Style)
# ==========================================

st.title("microbiONT")

# 1. CSS set (Chat specific)
st.markdown("""
<style>
    /* hide icon */
    .stChatMessageAvatar { display: none !important; }
    
    /* remove background */
    .stChatMessage { background-color: transparent !important; border: none !important; }
    
    /* chat-row */
    .chat-row { display: flex; width: 100%; margin-bottom: 10px; }
    .row-user { justify-content: flex-end; }
    .row-ai   { justify-content: flex-start; }

    /* bubble */
    .bubble {
        padding: 10px 15px; border-radius: 12px; max-width: 75%;
        word-wrap: break-word; font-family: "Source Sans Pro", sans-serif; line-height: 1.5; font-size: 16px;
    }
    
    /* User (right) */
    .user-bubble {
        background-color: #b0e0e6; color: black;
        border-bottom-right-radius: 2px; box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }
    
    /* AI (left) */
    .ai-bubble {
        background-color: #F0F2F6; border: 1px solid #ddd; color: #333;
        border-bottom-left-radius: 2px; box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }
    
    /* === Terminal input === */
    .stTextArea textarea {
        background-color: #222122 !important; 
        color: #FFFFFF !important;          
        font-family: 'Consolas', monospace !important; 
        border: 1px solid #222122 !important;
        
        /* 1. caret-color */
        caret-color: #FFFFFF !important;     
    }

    /* 2. Focus，green and light */
    .stTextArea textarea:focus {
        border: 1px solid #00ff00 !important;
        box-shadow: 0 0 1px rgba(201, 197, 201, 1) !important;
    }

    /* 3. click color */
    .stTextArea textarea::selection {
        background-color: #FFFFFF !important;
        color: #222122 !important;
    }
</style>
""", unsafe_allow_html=True)


# 2. message core logic
for idx, msg in enumerate(st.session_state.messages):
    
    # --- Type A: User Text  ---
    if msg["role"] == "user":
        st.markdown(f"""
        <div class="chat-row row-user">
            <div class="bubble user-bubble">{msg["content"]}</div>
        </div>
        """, unsafe_allow_html=True)

    # --- Type A: AI Text ---
    elif msg.get("type", "text") == "text":
        
        c1, c2 = st.columns([0.85, 0.15])
        with c1:
            st.markdown(f"""<div class="bubble ai-bubble">{msg["content"]}</div>""", unsafe_allow_html=True)

    # --- Type B: Terminal Card  ---
    elif msg.get("type") == "terminal":
       
        c1, c2 = st.columns([0.85, 0.15])
        with c1:
            st.caption("💻 Terminal Request (editable)")
            with st.container(border=True):
                cmd_val = st.text_area(
                    "Script", 
                    msg["content"], 
                    height=150, 
                    key=f"cmd_input_{idx}", 
                    label_visibility="collapsed"
                )
                
                
                if st.button("RUN", key=f"btn_run_{idx}", type="primary", use_container_width=True):
                    st.session_state.is_executing = True
                    st.session_state.target_cmd = cmd_val
                    st.rerun()

    # --- Type C: Log  ---
    elif msg.get("type") == "log":
        c1, c2 = st.columns([0.85, 0.15]) 
        with c1:
            st.caption(f"System Log ({msg.get('timestamp', '')})")
            
            with st.expander("View Output", expanded=False):
                
                with st.container(height=300):
                    st.code(msg["content"], language="bash")
            
            st.download_button("Download Log", msg["content"], f"log_{idx}.txt", key=f"dl_{idx}")

    # --- Type D: Report ---
    elif msg.get("type") == "report":
        c1, c2 = st.columns([0.9, 0.1])
        with c1:
            st.caption(f"📊 Report: {msg.get('content')}")
            qc_dir = msg.get("qc_dir", "")
            pc_dir = msg.get("pc_dir", "")
            
            if os.path.exists(qc_dir):
                display_qc_report(qc_dir, pc_dir, key_suffix=str(idx))
            else:
                st.error(f"Path not found: {qc_dir}")

# ==========================================
# 3. logic ( STOP and realtime Log)
# ==========================================

if st.session_state.is_executing and st.session_state.get("target_cmd"):
   
    run_log = "latest_run.log"
    run_exit = "latest_run.exit"
    
    
    if os.path.exists(run_exit): os.remove(run_exit)
    if os.path.exists(run_log): os.remove(run_log)
    
   
    safe_cmd = f"{{ {st.session_state.target_cmd} ; }} > {run_log} 2>&1 ; echo $? > {run_exit}"
    
    
    process = subprocess.Popen(
        safe_cmd, 
        shell=True, 
        executable='/bin/bash', 
        preexec_fn=os.setsid
    )
    
   
    st.session_state.pid = process.pid
    st.session_state.is_running = True
    st.session_state.is_executing = False 
    st.session_state.log_file = run_log
    st.session_state.exit_file = run_exit
    st.rerun()


if st.session_state.get("is_running"):
    
    # lodding Log
    log_content = ""
    if os.path.exists(st.session_state.log_file):
        with open(st.session_state.log_file, "r") as f:
            log_content = f.read()

    
    col_ctrl, col_space = st.columns([0.85, 0.15])
    with col_ctrl:
        show_live_log = st.checkbox("Expand Live Log", value=True, key="chk_live_log")

    c1, c2 = st.columns([0.85, 0.15])
    with c1:
        
        with st.status("Executing... (Running in background)", expanded=show_live_log) as status:
            st.write("Initializing...")
            st.code(st.session_state.target_cmd, language="bash")
            st.markdown("---")
            st.caption("Latest Output:")
            
            st.code(log_content[-3000:], language="text")
            
    with c2:
        # 🔴 STOP 
        if st.button("🛑 STOP", type="primary", key="btn_stop_process"):
            if st.session_state.pid:
                try:
                  
                    os.killpg(os.getpgid(st.session_state.pid), signal.SIGTERM)
                except Exception:
                    pass
            
            st.session_state.is_running = False
            
            import datetime
            final_log = f"[STOPPED BY USER]\n" + "-"*40 + "\n" + log_content
            st.session_state.messages.append({
                "role": "assistant", "type": "log", "content": final_log,
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            })
            st.rerun()

   
    if os.path.exists(st.session_state.exit_file):
        st.session_state.is_running = False
        
        with open(st.session_state.exit_file, "r") as f:
            try:
                exit_code = int(f.read().strip())
            except:
                exit_code = 1 
        
        if exit_code == 0:
            prefix = "[SUCCESS]\n"
        else:
            prefix = f"[ERROR] Exit Code: {exit_code}\n"
            
        final_log = prefix + "-"*40 + "\n" + log_content
        
        import datetime
        st.session_state.messages.append({
            "role": "assistant", "type": "log", "content": final_log,
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
        })
        st.rerun()
        
    
    time.sleep(1)
    st.rerun()

# 4. Chat Input
if prompt := st.chat_input("Ask or request command..."):
    
    st.session_state.messages.append({"role": "user", "type": "text", "content": prompt})
    
    with st.spinner("AI thinking..."):
        ctx = f"Settings: Input={st.session_state.get('s_d_in', 'Not set')}"
        resp = ask_ai(prompt, ctx)
        
        has_cmd, extracted_cmd = parse_mixed_response(resp)
        
        if has_cmd:
            text_part = resp.replace(extracted_cmd, "").replace("```bash", "").replace("```", "").strip()
            if text_part:
                st.session_state.messages.append({"role": "assistant", "type": "text", "content": text_part})
            
            fixed_cmd = auto_fix_command(extracted_cmd)
            st.session_state.messages.append({"role": "assistant", "type": "terminal", "content": fixed_cmd})
        else:
            st.session_state.messages.append({"role": "assistant", "type": "text", "content": resp})
            
    st.rerun()
