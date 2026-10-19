import React from 'react';

type Props = {
  children: React.ReactNode;
};

export const Toast = ({ children }: Props) => {
  return <div className="launchpad-toast__content flex">{children}</div>;
};
