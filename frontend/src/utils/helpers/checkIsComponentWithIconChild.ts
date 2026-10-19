import { Children, isValidElement, ReactNode } from 'react';

/**
 * Has to be kind of absolute path using alias due to
 * this helper imports the component being the helper himself
 */
import { Icon } from '@components/Shared/Icon';

/**
 * The purpose of this is checking to apply
 * styles to Link or Button with icon
 */
export const checkIsComponentWithIconChild = (children: ReactNode) =>
  Children.toArray(children).some((child) =>
    isValidElement(child) ? child.type === Icon : false,
  );
