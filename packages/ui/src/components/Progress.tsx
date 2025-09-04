import * as React from 'react';
import * as ProgressPrimitive from '@radix-ui/react-progress';
import { cn } from '../utils';

interface ProgressProps extends React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root> {
  variant?: 'default' | 'alice' | 'guardian';
  showValue?: boolean;
}

const Progress = React.forwardRef<React.ElementRef<typeof ProgressPrimitive.Root>, ProgressProps>(
  ({ className, value, variant = 'default', showValue = false, ...props }, ref) => {
    const getIndicatorColor = () => {
      if (variant === 'guardian') {
        const numValue = value || 0;
        if (numValue < 70) return 'bg-green-500';
        if (numValue < 85) return 'bg-yellow-500';
        return 'bg-red-500';
      }
      if (variant === 'alice') return 'bg-alice-primary';
      return 'bg-primary';
    };

    return (
      <div className="relative">
        <ProgressPrimitive.Root
          ref={ref}
          className={cn('relative h-4 w-full overflow-hidden rounded-full bg-secondary', className)}
          {...props}
        >
          <ProgressPrimitive.Indicator
            className={cn('h-full w-full flex-1 transition-all', getIndicatorColor())}
            style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
          />
        </ProgressPrimitive.Root>
        {showValue && (
          <div className="absolute inset-0 flex items-center justify-center text-xs font-medium text-white">
            {value}%
          </div>
        )}
      </div>
    );
  },
);
Progress.displayName = ProgressPrimitive.Root.displayName;

export { Progress };
