import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "../utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
        success: "border-transparent bg-green-500 text-white hover:bg-green-500/80",
        warning: "border-transparent bg-yellow-500 text-white hover:bg-yellow-500/80",
        // Alice-specific variants
        guardian: {
          normal: "status-green",
          brownout: "status-yellow", 
          degraded: "status-yellow",
          emergency: "status-red",
          lockdown: "status-red"
        },
        alice: "border-alice-accent/30 bg-alice-accent/10 text-alice-accent",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  guardianStatus?: 'normal' | 'brownout' | 'degraded' | 'emergency' | 'lockdown'
}

function Badge({ className, variant, guardianStatus, ...props }: BadgeProps) {
  // Handle Guardian status badges
  if (variant === 'guardian' && guardianStatus) {
    const statusClasses = {
      normal: 'status-green',
      brownout: 'status-yellow', 
      degraded: 'status-yellow',
      emergency: 'status-red',
      lockdown: 'status-red'
    }
    
    return (
      <div
        className={cn(
          "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
          statusClasses[guardianStatus],
          className
        )}
        {...props}
      />
    )
  }

  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }