type GridHeaderProps = {
  columnTemplate: string;
};

export default function GridHeader({ columnTemplate }: GridHeaderProps) {
  return (
    <div
      className="sticky top-0 z-30 grid border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 backdrop-blur-md text-[10px] font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400 shadow-sm"
      style={{ gridTemplateColumns: columnTemplate }}
    >
      <div className="px-3 py-3 border-r border-slate-200 dark:border-slate-800">WBS Code</div>
      <div className="px-3 py-3 border-r border-slate-200 dark:border-slate-800">Task Description</div>
      <div className="px-3 py-3 border-r border-slate-200 dark:border-slate-800">Mode</div>
      <div className="px-3 py-3 border-r border-slate-200 dark:border-slate-800">Start Date</div>
      <div className="px-3 py-3 border-r border-slate-200 dark:border-slate-800">Finish Date</div>
      <div className="px-3 py-3 border-r border-slate-200 dark:border-slate-800 text-center">Duration</div>
      <div className="px-3 py-3 border-r border-slate-200 dark:border-slate-800 text-center">% Comp</div>
      <div className="px-3 py-3 border-r border-slate-200 dark:border-slate-800 text-center">Status</div>
      <div className="px-3 py-3 border-r border-slate-200 dark:border-slate-800 text-center">Heads</div>
      <div className="px-3 py-3 border-r border-slate-200 dark:border-slate-800">Constraint</div>
      <div className="px-3 py-3 text-right">Menu</div>
    </div>
  );
}
