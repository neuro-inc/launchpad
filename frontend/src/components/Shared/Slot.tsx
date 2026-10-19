type Props = {
  slot?: React.ReactNode;
  children?: React.ReactNode;
};

export const Slot = ({ slot, children }: Props) => {
  const content = slot ?? children;

  // eslint-disable-next-line react/jsx-no-useless-fragment
  return <>{content}</>;
};
