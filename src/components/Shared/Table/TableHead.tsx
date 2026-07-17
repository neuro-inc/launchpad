import clsx from 'clsx';

type Props = React.ThHTMLAttributes<HTMLTableCellElement> & {
  children?: React.ReactNode;
};

export const TableHead = ({ className, style, children, ...props }: Props) => (
  <th
    {...props}
    className={clsx(
      'launchpad-table__head sticky top-0 z-10 p-4 text-left font-400 text-black',
      className,
    )}
    style={style}
  >
    {children}
  </th>
);
