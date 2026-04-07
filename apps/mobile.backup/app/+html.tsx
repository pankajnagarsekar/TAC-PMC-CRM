import { ScrollViewStyleReset } from 'expo-router/html';
import { type PropsWithChildren } from 'react';

/**
 * This file is web-only and used to configure the root HTML for every web page during static rendering.
 * The contents of this function only run in Node.js and are never shared with the browser.
 */
export default function Root({ children }: PropsWithChildren) {
    return (
        <html lang="en">
            <head>
                <meta charSet="utf-8" />
                <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
                <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />

                {/* 
          Disable body scrolling on web. This makes ScrollView components work as expected. 
          https://docs.expo.dev/router/appearance/#root-html
        */}
                <ScrollViewStyleReset />

                {/* Add any additional <head> elements here (favicons, etc.) */}
                <style dangerouslySetInnerHTML={{ __html: expoRootStyles }} />
            </head>
            <body>{children}</body>
        </html>
    );
}

const expoRootStyles = `
#root, body, html {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}
`;
