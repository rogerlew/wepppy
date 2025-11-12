import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

type AuroraBackgroundProps = {
  className?: string
  children?: ReactNode
  opacity?: number
}

export function AuroraBackground({ className, children, opacity = 1 }: AuroraBackgroundProps) {
  return (
    <div className={cn('relative flex flex-col bg-slate-950', className)}>
      <div
        className="pointer-events-none fixed inset-x-0 top-0 z-0 h-screen mix-blend-screen"
        style={{ opacity }}
      >
        <motion.div
          initial={{ opacity: 0.4, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 2, ease: 'easeOut' }}
          className="aurora-debug absolute inset-0"
        >
          <div className="aurora aurora-one" />
          <div className="aurora aurora-two" />
          <div className="aurora aurora-three" />
          <div className="aurora aurora-four" />
        </motion.div>
      </div>
      <div className="relative z-10 flex h-full flex-col">{children}</div>
    </div>
  )
}
