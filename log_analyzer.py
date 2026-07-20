import os
import sys
import tarfile
import tkinter as tk
from tkinter import filedialog
import html
import csv
import io
import base64

MAX_PRINT_COUNT = 10
ICON_FILENAME = "my_icon.ico"

BASE_TARGET_PHRASES = {
    "Installation finished successfully": "에이전트 설치 완료",
    "disk scanner created": "Full Disk Scan 작업 생성",
    "disk scan started from": "Full Disk Scan 시작",
    "disk scan finished": "Full Disk Scan 정상 종료",
    "/opt/sentinelone/bin/sentinelctl control restart": "에이전트 재시작",
    "memory_limiter: Waiting for process agent": "에이전트 메모리 부하",
    "dns error: failed to lookup address": "DNS 조회 실패",
    "Failed to open connection": "콘솔 통신 실패",
    "Failed to send DV packet": "DV(Deep Visibility) 전송 실패",
    "Agent upgrade successful": "에이전트 업그레이드 성공",
    "Failed agent upgrade": "에이전트 업그레이드 실패",
    "Could not stop agent": "에이전트 중지 실패"
}

def get_icon_path():
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, ICON_FILENAME)
    return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ICON_FILENAME)

def set_window_icon(window, icon_path):
    try:
        if os.path.exists(icon_path):
            window.iconbitmap(icon_path)
            window.iconbitmap(default=icon_path)
    except Exception:
        pass

def show_custom_message(parent, title, message, icon_path):
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    
    set_window_icon(dialog, icon_path)
    
    dialog.grab_set()
    dialog.attributes('-topmost', True)
    
    dialog.geometry("450x180")
    dialog.resizable(False, False)
    
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - dialog.winfo_reqwidth()) // 2
    y = (dialog.winfo_screenheight() - dialog.winfo_reqheight()) // 2
    dialog.geometry(f"+{x}+{y}")

    msg_label = tk.Label(dialog, text=message, justify="center", padx=10, pady=15, wraplength=400)
    msg_label.pack(expand=True, fill="both")
    
    btn = tk.Button(dialog, text="확인", command=dialog.destroy, width=10)
    btn.pack(pady=10)
    
    parent.wait_window(dialog)

def ask_search_mode(parent, icon_path):
    dialog = tk.Toplevel(parent)
    dialog.title("로그 분석 모드 선택")
    
    set_window_icon(dialog, icon_path)
    dialog.grab_set()
    dialog.attributes('-topmost', True)
    
    dialog.geometry("350x180")
    dialog.resizable(False, False)
    
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - dialog.winfo_reqwidth()) // 2
    y = (dialog.winfo_screenheight() - dialog.winfo_reqheight()) // 2
    dialog.geometry(f"+{x}+{y}")

    tk.Label(dialog, text="원하시는 로그 분석 방식을 선택하세요.", font=("", 11, "bold"), pady=15).pack()

    mode_result = []

    def set_mode(mode):
        mode_result.append(mode)
        dialog.destroy()

    def on_cancel():
        mode_result.append(None)
        dialog.destroy()

    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=10)
    
    tk.Button(btn_frame, text="자동 로그 분석", height=2, width=15, command=lambda: set_mode('base')).pack(side="left", padx=10)
    tk.Button(btn_frame, text="로그 검색", height=2, width=15, command=lambda: set_mode('custom')).pack(side="left", padx=10)

    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    parent.wait_window(dialog)
    
    return mode_result[0] if mode_result else None

def ask_search_keywords(parent, icon_path):
    dialog = tk.Toplevel(parent)
    dialog.title("사용자 지정 로그 검색")
    
    set_window_icon(dialog, icon_path)
    dialog.grab_set()
    dialog.attributes('-topmost', True)
    
    dialog.geometry("400x300")
    dialog.resizable(False, False)
    
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - dialog.winfo_reqwidth()) // 2
    y = (dialog.winfo_screenheight() - dialog.winfo_reqheight()) // 2
    dialog.geometry(f"+{x}+{y}")

    tk.Label(dialog, text="검색할 로그를 입력하세요 (최대 5개):", pady=10).pack()
    
    entries = []
    
    for i in range(5):
        frame = tk.Frame(dialog)
        frame.pack(pady=3)
        tk.Label(frame, text=f"{i+1}.").pack(side="left")
        entry_var = tk.StringVar()
        entry = tk.Entry(frame, textvariable=entry_var, width=40)
        entry.pack(side="left", padx=5)
        entries.append(entry_var)
        
        if i == 0:
            entry.focus_set()

    result = []

    def on_confirm(event=None):
        valid_keywords = []
        for var in entries:
            val = var.get().strip()
            if val and val not in valid_keywords:
                valid_keywords.append(val)
                
        if valid_keywords:
            result.extend(valid_keywords)
            dialog.destroy()
        else:
            show_custom_message(dialog, "안내", "최소 1개의 검색어를 입력해주세요.", icon_path)

    def on_cancel(event=None):
        result.append(None)
        dialog.destroy()

    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=15)
    
    tk.Button(btn_frame, text="확인", command=on_confirm, width=8).pack(side="left", padx=5)
    tk.Button(btn_frame, text="취소", command=on_cancel, width=8).pack(side="left", padx=5)
    
    dialog.bind('<Return>', on_confirm)
    dialog.bind('<Escape>', on_cancel)

    parent.wait_window(dialog)
    
    return result if not (result and result[0] is None) else None

def get_output_filename(tar_filepath):
    if getattr(sys, 'frozen', False):
        save_dir = os.path.dirname(sys.executable)
    else:
        save_dir = os.path.dirname(os.path.abspath(__file__))
        
    base_name = os.path.basename(tar_filepath)
    
    if base_name.endswith('.tar.gz'):
        name_without_ext = base_name[:-7]
    elif base_name.endswith('.tgz'):
        name_without_ext = base_name[:-4]
    elif base_name.endswith('.tar'):
        name_without_ext = base_name[:-4]
    else:
        name_without_ext = os.path.splitext(base_name)[0]
        
    output_filename = os.path.join(save_dir, f"{name_without_ext}.html")
    
    counter = 1
    while os.path.exists(output_filename):
        output_filename = os.path.join(save_dir, f"{name_without_ext}_{counter}.html")
        counter += 1
        
    return output_filename

def select_file_and_search():
    root = tk.Tk()
    
    icon_path = get_icon_path()
    set_window_icon(root, icon_path)
    root.withdraw() 

    tar_filepath = filedialog.askopenfilename(
        title="로그 파일(.tar.gz)을 선택하세요",
        filetypes=[("Tar Gz files", "*.tar.gz;*.tgz"), ("Tar files", "*.tar"), ("All files", "*.*")]
    )

    if not tar_filepath:
        root.destroy()
        return

    search_mode = ask_search_mode(root, icon_path)
    
    if not search_mode:
        show_custom_message(root, "안내", "작업이 취소되었습니다.", icon_path)
        root.destroy()
        return

    final_target_phrases = {}
    
    if search_mode == 'base':
        final_target_phrases = BASE_TARGET_PHRASES.copy()
        summary_title = "자동 로그 분석 결과"
        summary_keyword_html = "<p><strong>분석 모드:</strong> 자동 로그 분석</p>"
        
    elif search_mode == 'custom':
        custom_keywords = ask_search_keywords(root, icon_path)
        if not custom_keywords:
            show_custom_message(root, "안내", "검색어가 입력되지 않아 취소되었습니다.", icon_path)
            root.destroy()
            return
            
        for kw in custom_keywords:
            final_target_phrases[kw] = f"사용자 검색어: {kw}"
            
        custom_keywords_str = ", ".join(custom_keywords)
        summary_title = "사용자 지정 로그 검색 결과"
        summary_keyword_html = f"<p><strong>검색 키워드:</strong> <span style='color:#c0392b; font-weight:bold;'>{html.escape(custom_keywords_str)}</span> </p>"

    output_filepath = get_output_filename(tar_filepath)
    
    phrase_matches = {phrase: [] for phrase in final_target_phrases}
    found_any_global = False

    try:
        with tarfile.open(tar_filepath, 'r:*') as tar:
            for member in tar.getmembers():
                if member.isfile():
                    f = tar.extractfile(member)
                    if f is None:
                        continue
                    
                    for line in f:
                        decoded_line = None
                        for encoding in ['utf-8', 'cp949', 'euc-kr']:
                            try:
                                decoded_line = line.decode(encoding)
                                break
                            except UnicodeDecodeError:
                                continue
                        
                        if decoded_line is None:
                            continue 
                        
                        decoded_line_lower = decoded_line.lower()
                        
                        for phrase in final_target_phrases:
                            if phrase.strip().lower() in decoded_line_lower:
                                phrase_matches[phrase].append((decoded_line.strip(), member.name))
                                found_any_global = True
                                break

        csv_io = io.StringIO()
        csv_writer = csv.writer(csv_io)
        csv_writer.writerow(["분류", "검색 키워드(Keyword)", "파일명(Filename)", "로그 내용(Log Line)"])

        txt_lines = []
        txt_lines.append(f"=== {summary_title} ===")
        txt_lines.append(f"분석 대상: {tar_filepath}")
        if search_mode == 'custom':
            txt_lines.append(f"검색 키워드: {custom_keywords_str}")
        txt_lines.append("=" * 70)

        for phrase, description in final_target_phrases.items():
            matches = phrase_matches[phrase]
            if not matches:
                continue
            
            matches.sort(key=lambda x: x[0], reverse=True)
            txt_lines.append(f"\n[{description}]")
            txt_lines.append(f"Search Pattern: {phrase}")
            txt_lines.append("-" * 70)
            
            for line, filename in matches:
                csv_writer.writerow([description, phrase, filename, line])
                txt_lines.append(f"[{filename}] {line}")

        csv_data_b64 = base64.b64encode(csv_io.getvalue().encode('utf-8-sig')).decode('utf-8')
        txt_data_b64 = base64.b64encode("\n".join(txt_lines).encode('utf-8')).decode('utf-8')

        html_content = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <title>로그 분석 보고서</title>
            <style>
                body {{ font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; background-color: #f4f7f6; color: #333; margin: 20px auto; max-width: 1200px; line-height: 1.4; }}
                h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; text-align: center; font-size: 1.5em; margin-bottom: 15px; }}
                .summary-box {{ background: #fff; padding: 15px 20px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 15px; border-left: 4px solid #2ecc71; display: flex; justify-content: space-between; align-items: center; }}
                .summary-text p {{ margin: 3px 0; font-size: 1em; }}
                .btn-group {{ display: flex; gap: 10px; }}
                .download-btn {{ background-color: #3498db; color: white; border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; font-size: 0.9em; font-weight: bold; transition: 0.2s; }}
                .download-btn:hover {{ background-color: #2980b9; }}
                .download-btn.txt-btn {{ background-color: #34495e; }}
                .download-btn.txt-btn:hover {{ background-color: #2c3e50; }}
                .card {{ background: #fff; margin-bottom: 15px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden; }}
                .card-header {{ background: #34495e; color: #fff; padding: 8px 15px; font-weight: bold; font-size: 1.05em; display: flex; justify-content: space-between; align-items: center; }}
                .badge {{ background: #e74c3c; padding: 2px 8px; border-radius: 12px; font-size: 0.75em; font-weight: normal; }}
                .card-body {{ padding: 12px 15px; }}
                .pattern {{ color: #c0392b; font-weight: bold; margin-bottom: 8px; display: inline-block; background: #fadbd8; padding: 3px 8px; border-radius: 3px; font-size: 0.9em; }}
                .filename {{ font-weight: bold; color: #2980b9; margin: 8px 0 4px 0; font-size: 0.95em; border-bottom: 1px dashed #bdc3c7; padding-bottom: 2px; }}
                .log-line {{ background: #ecf0f1; padding: 6px 10px; border-left: 3px solid #95a5a6; margin-bottom: 4px; font-family: 'Consolas', monospace; font-size: 0.85em; word-break: break-all; color: #2c3e50; }}
                .omitted {{ color: #7f8c8d; font-style: italic; margin-top: 10px; font-size: 0.85em; background: #fdfefe; padding: 10px; border: 1px solid #e5e8e8; border-radius: 3px; text-align: center; }}
                .no-error {{ background: #fff; padding: 30px; text-align: center; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-size: 1.1em; color: #27ae60; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>{html.escape(summary_title)}</h1>
            <div class="summary-box">
                <div class="summary-text">
                    <p><strong>분석 대상:</strong> {tar_filepath}</p>
                    {summary_keyword_html}
                </div>
        """
        
        if found_any_global:
            html_content += f"""
                <div class="btn-group">
                    <button onclick="downloadFile('csv')" class="download-btn">CSV 다운로드 (전체)</button>
                    <button onclick="downloadFile('txt')" class="download-btn txt-btn">TXT 다운로드 (전체)</button>
                </div>
            """

        html_content += "</div>"

        if not found_any_global:
            html_content += f'<div class="no-error">일치하는 로그가 없습니다.</div>'
        else:
            for phrase, description in final_target_phrases.items():
                matches = phrase_matches[phrase]
                if not matches:
                    continue 
                
                matches.sort(key=lambda x: x[0], reverse=True)
                total_count = len(matches)
                top_matches = matches[:MAX_PRINT_COUNT]
                
                html_content += f"""
                <div class="card">
                    <div class="card-header">
                        <span>[{description}]</span>
                        <span class="badge">총 {total_count}건 발견</span>
                    </div>
                    <div class="card-body">
                        <div class="pattern">Search Pattern: {html.escape(phrase)}</div>
                """
                
                grouped_matches = {}
                for line, filename in top_matches:
                    if filename not in grouped_matches:
                        grouped_matches[filename] = []
                    grouped_matches[filename].append(line)
                    
                for filename, lines in grouped_matches.items():
                    html_content += f'<div class="filename">[{html.escape(filename)}]</div>'
                    for line in lines:
                        safe_line = html.escape(line)
                        html_content += f'<div class="log-line">{safe_line}</div>'
                        
                if total_count > MAX_PRINT_COUNT:
                    html_content += f"""
                        <div class="omitted">
                            최신 {MAX_PRINT_COUNT}건만 표시됩니다. 생략된 {total_count - MAX_PRINT_COUNT}건의 로그는 <b>상단 다운로드 버튼</b>을 통해 전체 확인이 가능합니다.
                        </div>
                    """
                    
                html_content += """
                    </div>
                </div>
                """

        base_name_for_dl = os.path.splitext(os.path.basename(output_filepath))[0]
        
        html_content += f"""
        <script>
        const csvData = "{csv_data_b64}";
        const txtData = "{txt_data_b64}";

        function b64toBlob(b64Data, contentType='') {{
            const byteCharacters = atob(b64Data);
            const byteArrays = [];
            for (let offset = 0; offset < byteCharacters.length; offset += 512) {{
                const slice = byteCharacters.slice(offset, offset + 512);
                const byteNumbers = new Array(slice.length);
                for (let i = 0; i < slice.length; i++) {{
                    byteNumbers[i] = slice.charCodeAt(i);
                }}
                const byteArray = new Uint8Array(byteNumbers);
                byteArrays.push(byteArray);
            }}
            return new Blob(byteArrays, {{type: contentType}});
        }}

        function downloadFile(type) {{
            let b64 = type === 'csv' ? csvData : txtData;
            let mime = type === 'csv' ? 'text/csv;charset=utf-8-sig;' : 'text/plain;charset=utf-8;';
            let ext = type === 'csv' ? 'csv' : 'txt';
            
            const blob = b64toBlob(b64, mime);
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `{base_name_for_dl}_Result.${{ext}}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}
        </script>
        </body>
        </html>
        """

        with open(output_filepath, "w", encoding="utf-8") as out_f:
            out_f.write(html_content)

        save_dir = os.path.dirname(output_filepath)
        success_msg = f"분석이 완료되었습니다.\n\n[저장 경로]\n{save_dir}\n\n확인을 누르면 분석 결과가 열립니다."
        show_custom_message(root, "분석 완료", success_msg, icon_path)
        
        os.startfile(output_filepath)

    except Exception as e:
        show_custom_message(root, "에러", f"오류가 발생했습니다:\n{str(e)}", icon_path)
    finally:
        root.destroy()

if __name__ == "__main__":
    select_file_and_search()