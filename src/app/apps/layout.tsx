import SetCookieClient from '@components/Auth/SetCookieClient';
import { Layout } from '@components/Ui';

type Props = {
  children: React.ReactNode;
};

const PageLayout: React.FC<Props> = ({ children }) => {
  return (
    <Layout.Wrapper>
      <SetCookieClient />
      {children}
    </Layout.Wrapper>
  );
};

export default PageLayout;
