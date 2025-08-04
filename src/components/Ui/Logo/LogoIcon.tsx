import { cn } from '@utils';

type Props = {
  className?: string;
};

export const LogoIcon: React.FC<Props> = ({ className }) => {
  return (
    <svg
      className={cn('size-8 text-black', className)}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 32 32"
      fill="currentColor"
    >
      <g clipPath="url(#clip0_1_1779)">
        <path d="M11 0H21V10L11 0Z" fill="#00F0A5" />
        <path d="M11 11H21V21L11 11Z" fill="#00F0A5" />
        <path d="M22 0H32V10L22 0Z" fill="#00F0A5" />
        <path d="M22 11H32V21L22 11Z" fill="#00F0A5" />
        <path d="M0 0H8V32H0V0Z" fill="url(#paint0_linear_1_1779)" />
        <path d="M8 24H32V32H8V24Z" fill="url(#paint1_linear_1_1779)" />
      </g>
      <defs>
        <linearGradient
          id="paint0_linear_1_1779"
          x1="52.5"
          y1="-16"
          x2="74.1357"
          y2="32.852"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#272782" />
          <stop offset="0.37" stopColor="#5F5FC9" />
          <stop offset="0.69" stopColor="#48D0FF" />
          <stop offset="1" stopColor="#00FFB0" />
        </linearGradient>
        <linearGradient
          id="paint1_linear_1_1779"
          x1="52.5"
          y1="-16"
          x2="74.1357"
          y2="32.852"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#272782" />
          <stop offset="0.37" stopColor="#5F5FC9" />
          <stop offset="0.69" stopColor="#48D0FF" />
          <stop offset="1" stopColor="#00FFB0" />
        </linearGradient>
        <clipPath id="clip0_1_1779">
          <rect width="32" height="32" fill="white" />
        </clipPath>
      </defs>
    </svg>
  );
};
