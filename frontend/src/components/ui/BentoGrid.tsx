import React from 'react'
import { cn } from '../../lib/utils'
import { CardSpotlight } from './CardSpotlight'

export const BentoGrid = ({
  className,
  children,
}: {
  className?: string
  children?: React.ReactNode
}) => {
  return (
    <div
      className={cn(
        'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 max-w-7xl mx-auto',
        className
      )}
    >
      {children}
    </div>
  )
}

export const BentoGridItem = ({
  className,
  title,
  description,
  header,
  icon,
  eyebrow,
  action,
  spotlightColor = 'rgba(2, 132, 199, 0.05)',
  spotlightRadius = 320,
  children,
}: {
  className?: string
  title?: string | React.ReactNode
  description?: string | React.ReactNode
  header?: React.ReactNode
  icon?: React.ReactNode
  eyebrow?: string
  action?: React.ReactNode
  spotlightColor?: string
  spotlightRadius?: number
  children?: React.ReactNode
}) => {
  return (
    <CardSpotlight
      color={spotlightColor}
      radius={spotlightRadius}
      className={cn('group/bento flex flex-col justify-between', className)}
    >
      {/* Top Header / Eyebrow bar */}
      {(eyebrow || action) && (
        <div className="mb-3 flex items-center justify-between">
          {eyebrow && (
            <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-slate-500 font-semibold">
              {eyebrow}
            </span>
          )}
          {action && <div>{action}</div>}
        </div>
      )}

      {/* Visual Header slot */}
      {header && (
        <div className="flex-1 w-full min-h-[120px]">
          {header}
        </div>
      )}

      {/* Body content if present */}
      {children}

      {/* Demo 2 Signature Footer with hover translation */}
      {(title || description || icon) && (
        <div className="mt-4 pt-3 border-t border-slate-100 transition duration-200 group-hover/bento:translate-x-1">
          <div className="flex items-center gap-2">
            {icon && (
              <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-slate-700">
                {icon}
              </div>
            )}
            {title && (
              <div className="font-sans text-sm font-semibold tracking-tight text-slate-900">
                {title}
              </div>
            )}
          </div>
          {description && (
            <div className="mt-1 font-sans text-xs text-slate-500 leading-relaxed">
              {description}
            </div>
          )}
        </div>
      )}
    </CardSpotlight>
  )
}
