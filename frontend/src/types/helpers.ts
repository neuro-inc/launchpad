import { VariantProps } from 'tailwind-variants';

import {
  buttonVariants,
  chaseSpinnerVariants,
  layoutContainerVariants,
} from '@utils/variants';

export { type VariantProps } from 'tailwind-variants';

export namespace Variant {
  export type Props<T extends (...args: any) => any> = VariantProps<T>;

  export type Button = VariantProps<typeof buttonVariants>;

  export type ChaseSpinner = VariantProps<typeof chaseSpinnerVariants>;

  export type LayoutContainer = VariantProps<typeof layoutContainerVariants>;
}
