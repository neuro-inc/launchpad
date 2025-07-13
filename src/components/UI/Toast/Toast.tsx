import React from 'react';

type Props = {
  children: React.ReactNode;
};

export const Toast = ({ children }: Props) => {
  return <div className="flex">{children}</div>;
};
