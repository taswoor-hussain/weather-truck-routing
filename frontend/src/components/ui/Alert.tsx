import type { ReactNode } from 'react'

type Tone = 'error' | 'warning' | 'info'

const TONE_CLASSES: Record<Tone, string> = {
  error: 'bg-red-50 text-red-800 ring-red-200',
  warning: 'bg-amber-50 text-amber-900 ring-amber-200',
  info: 'bg-blue-50 text-blue-900 ring-blue-200',
}

interface AlertProps {
  tone?: Tone
  title?: string
  children: ReactNode
  action?: ReactNode
}

export function Alert({ tone = 'info', title, children, action }: AlertProps) {
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={`rounded-lg px-3.5 py-3 text-sm ring-1 ${TONE_CLASSES[tone]}`}
    >
      {title && <p className="font-semibold">{title}</p>}
      <div className={title ? 'mt-0.5' : undefined}>{children}</div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
