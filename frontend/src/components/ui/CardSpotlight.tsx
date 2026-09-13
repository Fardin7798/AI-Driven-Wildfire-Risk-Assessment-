import React from 'react'
import { motion, useMotionValue, useMotionTemplate } from 'framer-motion'
import { cn } from '../../lib/utils'

interface CardSpotlightProps extends React.HTMLAttributes<HTMLDivElement> {
  radius?: number
  color?: string
  children: React.ReactNode
  className?: string
}

export const CardSpotlight: React.FC<CardSpotlightProps> = ({
  children,
  radius = 320,
  color = 'rgba(2, 132, 199, 0.05)',
  className,
  ...props
}) => {
  const mouseX = useMotionValue(0)
  const mouseY = useMotionValue(0)

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const { left, top } = e.currentTarget.getBoundingClientRect()
    mouseX.set(e.clientX - left)
    mouseY.set(e.clientY - top)
  }

  return (
    <div
      className={cn(
        'group/spotlight relative flex flex-col justify-between overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition duration-300 hover:border-slate-300 hover:shadow-md',
        className
      )}
      onMouseMove={handleMouseMove}
      {...props}
    >
      {/* Subtle radial spotlight matching Post 1 light palette */}
      <motion.div
        className="pointer-events-none absolute -inset-px rounded-2xl opacity-0 transition-opacity duration-300 group-hover/spotlight:opacity-100"
        style={{
          background: useMotionTemplate`radial-gradient(${radius}px circle at ${mouseX}px ${mouseY}px, ${color}, transparent 80%)`,
        }}
        aria-hidden="true"
      />

      {/* Content wrapper */}
      <div className="relative z-10 flex h-full flex-col justify-between">
        {children}
      </div>
    </div>
  )
}
