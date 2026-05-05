import { Layout } from '@components/Ui';

type Props = {
  children: React.ReactNode;
};

const PageLayout: React.FC<Props> = ({ children }) => {
  return <Layout.Wrapper>{children}</Layout.Wrapper>;
};

export default PageLayout;
