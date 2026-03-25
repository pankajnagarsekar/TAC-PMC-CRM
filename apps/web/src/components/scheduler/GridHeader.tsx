type GridHeaderProps = {
  columnTemplate: string;
};

export default function GridHeader({ columnTemplate }: GridHeaderProps) {
  return (
    <div
      className="sticky top-0 z-30 grid border-b border-white/5 bg-gradient-to-b from-slate-900/80 to-slate-950/80 backdrop-blur-md text-[10px] font-black uppercase tracking-[0.18em] text-slate-400 shadow-sm"
      style={{ gridTemplateColumns: columnTemplate }}
    >
      <div className="px-3 py-3">WBS</div>
      <div className="px-3 py-3">Task</div>
      <div className="px-3 py-3">Mode</div>
      <div className="px-3 py-3">Start</div>
      <div className="px-3 py-3">Finish</div>
      <div className="px-3 py-3">Duration</div>
      <div className="px-3 py-3">% Complete</div>
      <div className="px-3 py-3">Status</div>
      <div className="px-3 py-3">Resources</div>
      <div className="px-3 py-3">Deadline</div>
      <div className="px-3 py-3 text-right">Actions</div>
    </div>
  );
}
