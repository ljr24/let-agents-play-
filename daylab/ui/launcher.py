"""Launcher responsibilities only."""
import json
import time
import webbrowser
from dataclasses import replace
from ..config import ExperimentConfig, LABELS, rules_text
from ..controllers import CloudConfig
from ..recording import ROOT
from .play import play
from .replay_view import replay_window


def launcher():
    import tkinter as tk
    import queue
    import threading
    from tkinter import ttk, messagebox, filedialog
    from ..reports import compare_runs, same_state_compare

    root = tk.Tk()
    root.title("pypvz · 白天实验室 V2")
    root.geometry("780x670")
    root.minsize(720, 620)
    frame = ttk.Frame(root, padding=22)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="白天实验室", font=("Microsoft YaHei UI", 24, "bold")).pack(anchor="w")
    ttk.Label(frame, text="默认六种植物 / 四种僵尸 · 可选实验配置 · 人机统一操作 · 记录与回放").pack(anchor="w", pady=(4, 16))
    settings = ttk.Frame(frame)
    settings.pack(fill="x")
    scenario, seed, actor = (
        tk.StringVar(value="经济建设"),
        tk.StringVar(value="42"),
        tk.StringVar(value="真人游玩"),
    )
    practice = tk.BooleanVar(value=False)
    for index, (label, variable, options) in enumerate(
        (("关卡", scenario, list(LABELS.values())), ("控制者", actor, ["真人游玩", "规则 AI", "云端 AI"]))
    ):
        ttk.Label(settings, text=label).grid(row=0, column=index * 2, padx=6)
        ttk.Combobox(
            settings, textvariable=variable, values=options, state="readonly", width=14
        ).grid(row=0, column=index * 2 + 1)
    ttk.Label(settings, text="种子").grid(row=0, column=4, padx=6)
    ttk.Entry(settings, textvariable=seed, width=9).grid(row=0, column=5)
    ttk.Checkbutton(frame, text="练习模式（允许重开，成绩不纳入正式比较）", variable=practice).pack(anchor="w", pady=12)
    experiment_path = tk.StringVar(value="")
    experiment_row = ttk.Frame(frame)
    experiment_row.pack(fill="x", pady=(0, 8))
    ttk.Label(experiment_row, text="实验配置：").pack(side="left")
    ttk.Entry(experiment_row, textvariable=experiment_path).pack(side="left", fill="x", expand=True)

    def choose_experiment():
        path = filedialog.askopenfilename(
            title="选择实验配置（空白使用上方关卡）",
            initialdir=str(ROOT / "configs"),
            filetypes=[("JSON", "*.json")],
        )
        if path:
            experiment_path.set(path)

    ttk.Button(experiment_row, text="选择", command=choose_experiment).pack(side="left", padx=8)
    ttk.Button(experiment_row, text="清空", command=lambda: experiment_path.set("")).pack(side="left")
    cloud_path = tk.StringVar(value=str(ROOT / "cloud.local.json"))
    cloudrow = ttk.Frame(frame)
    cloudrow.pack(fill="x")
    ttk.Label(cloudrow, text="云端配置：").pack(side="left")
    ttk.Entry(cloudrow, textvariable=cloud_path).pack(side="left", fill="x", expand=True)

    def choose_cloud():
        path = filedialog.askopenfilename(title="选择云端配置", filetypes=[("JSON", "*.json")])
        if path:
            cloud_path.set(path)

    ttk.Button(cloudrow, text="选择", command=choose_cloud).pack(side="left", padx=8)
    ttk.Label(frame, text="云端模式会将公开局面发送到所配置的服务，可能产生费用；密钥只从环境变量读取。", wraplength=715).pack(
        anchor="w", pady=8
    )
    runs = []
    cancel_jobs = threading.Event()
    job_running = False
    progress = tk.StringVar(value="")

    def exit_launcher():
        cancel_jobs.set()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", exit_launcher)
    listing = tk.Listbox(frame, selectmode="extended", height=10, font=("Microsoft YaHei UI", 10))

    def refresh():
        runs[:] = sorted((ROOT / "experiments").glob("*/manifest.json"), reverse=True)
        listing.delete(0, "end")
        for path in runs:
            try:
                manifest = json.loads(path.read_text(encoding="utf-8"))
                result = json.loads((path.parent / "result.json").read_text(encoding="utf-8"))
                listing.insert(
                    "end",
                    f'{path.parent.name} | {manifest["config"]["actor"]} | {LABELS[manifest["config"]["scenario"]]} | {result["status"]}',
                )
            except (OSError, ValueError, KeyError):
                listing.insert("end", path.parent.name + " | 记录未完成")

    def selected():
        indices = listing.curselection()
        if not indices:
            raise ValueError("请先从列表选择记录。可按 Ctrl 多选。")
        return [runs[i].parent for i in indices]

    def guarded(fn):
        def run():
            try:
                fn()
            except Exception as exc:
                messagebox.showerror("未完成", str(exc))
            finally:
                root.deiconify()
                refresh()

        return run

    def start():
        kind = {"真人游玩": "human", "规则 AI": "rule", "云端 AI": "cloud"}[actor.get()]
        cloud = CloudConfig.load(cloud_path.get()) if kind == "cloud" else None
        if kind == "cloud" and not messagebox.askyesno(
            "确认云端调用", f"将调用 {cloud.model}\n服务：{cloud.base_url}\n每局最多 {cloud.max_requests} 次。继续？"
        ):
            return
        config = ExperimentConfig(
            scenario={v: k for k, v in LABELS.items()}[scenario.get()],
            actor=kind,
            practice=practice.get(),
        )
        if experiment_path.get().strip():
            with open(experiment_path.get().strip(), encoding="utf-8-sig") as stream:
                config = replace(
                    ExperimentConfig.from_dict(json.load(stream)),
                    actor=kind,
                    practice=practice.get(),
                )
        value = int(seed.get())
        root.withdraw()
        path = play(config, value, cloud_config=cloud)
        root.deiconify()
        messagebox.showinfo("记录已保存", str(path))

    ttk.Button(frame, text="开始实验", command=guarded(start)).pack(fill="x", pady=10)
    ttk.Label(frame, text="实验记录（Ctrl 多选后可比较；受干预和未完成记录会明确标记）").pack(anchor="w", pady=(8, 4))
    listing.pack(fill="both", expand=True)
    buttons = ttk.Frame(frame)
    buttons.pack(fill="x", pady=12)
    replay_at = tk.StringVar(value="0")

    def replay():
        path = selected()[0]
        at = float(replay_at.get())
        from ..recording import fingerprint

        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        mismatch = manifest["versions"] != fingerprint()
        if mismatch and not messagebox.askyesno(
            "旧版本记录", "记录版本与当前不同。可以逐步比较旧检查点，但不会标记为同版本验证通过。继续跨版本检查？"
        ):
            return
        root.withdraw()
        replay_window(path, at, migration_check=mismatch)

    def compare():
        paths = selected()
        report = compare_runs(
            paths, ROOT / "reports" / ("compare-" + time.strftime("%Y%m%d-%H%M%S"))
        )
        webbrowser.open(report.resolve().as_uri())

    def same_state():
        nonlocal job_running
        if job_running:
            raise ValueError("已有一个离线比较正在运行。")
        path = selected()[0]
        cloud = CloudConfig.load(cloud_path.get()) if actor.get() == "云端 AI" else None
        if cloud and not messagebox.askyesno("离线云端比较", "将发起模型调用（最多100个样本），可能产生费用。继续？"):
            return
        job_running = True
        progress.set("离线比较运行中；输入与结果将保存到 reports。关闭入口会停止后续请求。")
        completed = queue.Queue()
        destination = ROOT / "reports" / ("decisions-" + time.strftime("%Y%m%d-%H%M%S"))

        def work():
            try:
                completed.put(
                    (same_state_compare(path, destination, cloud, cancel_event=cancel_jobs), None)
                )
            except Exception as exc:
                completed.put((None, str(exc)))

        def poll_job():
            nonlocal job_running
            try:
                report, error = completed.get_nowait()
            except queue.Empty:
                root.after(200, poll_job)
                return
            job_running = False
            progress.set("离线比较完成。" if report else "离线比较未完成。")
            if error:
                messagebox.showerror("离线比较", error)
            else:
                webbrowser.open(report.resolve().as_uri())

        threading.Thread(target=work, daemon=True).start()
        root.after(200, poll_job)

    ttk.Button(buttons, text="回放", command=guarded(replay)).pack(side="left")
    ttk.Entry(buttons, textvariable=replay_at, width=6).pack(side="left", padx=5)
    ttk.Label(buttons, text="秒").pack(side="left", padx=(0, 14))
    ttk.Button(buttons, text="查看比较结果", command=guarded(compare)).pack(side="left", padx=4)
    ttk.Button(buttons, text="同局面比较", command=guarded(same_state)).pack(side="left", padx=4)
    ttk.Button(buttons, text="刷新", command=refresh).pack(side="right")

    def help_rules():
        config = ExperimentConfig()
        if experiment_path.get().strip():
            with open(experiment_path.get().strip(), encoding="utf-8-sig") as stream:
                config = ExperimentConfig.from_dict(json.load(stream))
        messagebox.showinfo(
            "共享规则",
            rules_text(config)
            + "\n\n鼠标选卡并种植，右键取消。1—6选当前页卡，左右键/滚轮翻页，S铲除，Enter等待，P暂停，Esc结束。界面行列为1起，接口为0起。",
        )

    ttk.Button(frame, text="规则与操作说明", command=guarded(help_rules)).pack(anchor="w")
    ttk.Label(frame, textvariable=progress, wraplength=715).pack(anchor="w")
    refresh()
    root.mainloop()
