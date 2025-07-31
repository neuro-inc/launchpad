import clsx from 'clsx';

type Props = {
  className?: string;
  children?: React.ReactNode;
};

export const TableHead = ({ className, children }: Props) => (
  <th
    className={clsx(
      'sticky top-0 z-10 p-4 text-left font-400 text-black',
      className,
    )}
  >
    {children}
  </th>
);
