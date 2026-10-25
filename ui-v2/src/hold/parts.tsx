// The two pieces the floating window (pro/Float.tsx) takes from here since the 25 Oct review (C8): the icons and the error
// guard. The rest went with the hold/* windows. Styles: ./hold.css (the Float's .hv classes).
import { Component } from 'react'
import type { ReactNode } from 'react'
import './hold.css'

const PATHS = {   // Lucide (ISC), inlined: the app carries no icon package
  Check: '<path d="M20 6 9 17l-5-5"/>',
  X: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  Minus: '<path d="M5 12h14"/>',
  Plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
  ChevronDown: '<path d="m6 9 6 6 6-6"/>',
  ChevronUp: '<path d="m18 15-6-6-6 6"/>',
  ArrowRight: '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  EyeOff: '<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.53 13.53 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><path d="m2 2 20 20"/>',
  SearchX: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="m13.5 8.5-5 5"/><path d="m8.5 8.5 5 5"/>',
  Ban: '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
  PiP: '<path d="M21 9V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v10c0 1.1.9 2 2 2h4"/><rect width="10" height="7" x="12" y="13" rx="2"/>',
  Undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5a5.5 5.5 0 0 1-5.5 5.5H11"/>',
}
export function Ico({ n, c = '' }: { n: keyof typeof PATHS; c?: string }) {
  return <svg className={`i ${c}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round"
              strokeLinejoin="round" aria-hidden="true" dangerouslySetInnerHTML={{ __html: PATHS[n] }} />
}

/** One broken render must never take the app, or the other view, down with it (REVIEW P1-20). */
export class Guard extends Component<{ children: ReactNode; name: string }, { err: string | null }> {
  state = { err: null as string | null }
  static getDerivedStateFromError(e: Error) { return { err: e.message } }
  render() {
    return this.state.err
      ? <div className="hv"><span className="err">The {this.props.name} hit a screen error ({this.state.err}). Press F5; the server and your records are untouched.</span></div>
      : this.props.children
  }
}
