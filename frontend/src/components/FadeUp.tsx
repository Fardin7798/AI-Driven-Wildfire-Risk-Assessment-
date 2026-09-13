'use client'

import { motion } from 'framer-motion'
import type { CSSProperties, ReactNode } from 'react'

type SupportedTags = 'div' | 'section' | 'span' | 'h1' | 'h2' | 'h3' | 'p' | 'nav' | 'header'

type FadeUpProps = {
  children: ReactNode
  delay?: number
  duration?: number
  y?: number
  className?: string
  style?: CSSProperties
  as?: SupportedTags
  once?: boolean
  id?: string
}

export function FadeUp({
  children,
  delay = 0,
  duration = 0.5,
  y = 20,
  className,
  style,
  as = 'div',
  once = true,
  id
}: FadeUpProps) {
  const Component = (motion as any)[as] || motion.div
  return (
    <Component
      id={id}
      className={className}
      style={style}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once, amount: 0.15 }}
      transition={{ duration, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </Component>
  )
}
