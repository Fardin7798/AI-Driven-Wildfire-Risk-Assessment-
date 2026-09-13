import React from 'react'
import { motion, type MotionProps } from 'framer-motion'

type SupportedElements = 'div' | 'section' | 'span' | 'h1' | 'h2' | 'h3' | 'p' | 'nav' | 'header' | 'article'

interface FadeUpProps extends MotionProps {
  children: React.ReactNode
  delay?: number
  duration?: number
  y?: number
  className?: string
  style?: React.CSSProperties
  as?: SupportedElements
  once?: boolean
}

export function FadeUp({
  children,
  delay = 0,
  duration = 0.5,
  y = 20,
  className = '',
  style,
  as = 'div',
  once = true,
  ...rest
}: FadeUpProps) {
  const Component = motion[as] as React.ElementType

  return (
    <Component
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once, amount: 0.15 }}
      transition={{
        duration,
        delay,
        ease: [0.22, 1, 0.36, 1]
      }}
      className={className}
      style={style}
      {...rest}
    >
      {children}
    </Component>
  )
}
