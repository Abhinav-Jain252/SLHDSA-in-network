#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <arpa/inet.h>
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/provider.h>


#define PORT 4433
// #define CERT_FILE "slhdsa.crt"
// #define KEY_FILE "slhdsa.key"


int main(int argc, char *argv[]) {

    signal(SIGPIPE, SIG_IGN);

    const char *cert_file = (argc >= 2) ? argv[1] : "slhdsa.crt";
    const char *key_file  = (argc >= 3) ? argv[2] : "slhdsa.key";

    OSSL_PROVIDER *default_provider = OSSL_PROVIDER_load(NULL,"default");
    if(default_provider == NULL) {
        printf("Error: couldn't load default provider\n");
        return 1;
    }

    OSSL_PROVIDER *oqs_provider = OSSL_PROVIDER_load(NULL,"oqsprovider");
    if(oqs_provider == NULL) {
        printf("Error: couldn't load oqsprovider\n");
        return 1;
    }


    // creating the TLS context
    SSL_CTX *ctx = SSL_CTX_new(TLS_server_method());
    if(ctx == NULL) {
        printf("Error: couldn't create SSL_CTX\n");
        return 1;
    }

    if(SSL_CTX_use_certificate_file(ctx, cert_file, SSL_FILETYPE_PEM)!=1) {
        printf("Error: couldn't load certificate file\n");
        return 1;
    }

    if(SSL_CTX_use_PrivateKey_file(ctx, key_file, SSL_FILETYPE_PEM)!=1) {
        printf("Error: couldn't load private key file\n");
        return 1;
    }

    // Create the socket and set an option
    int server_fd = socket(AF_INET,SOCK_STREAM,0);
    if(server_fd<0) {
        printf("Error: couldn't create socket\n");
        return 1;
    }

    int opt=1;
    setsockopt(server_fd,SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));


    // Bind to the port and start listening
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(PORT);


    if(bind(server_fd, (struct sockaddr*)&addr, sizeof(addr))<0) {
        printf("Error: couldn't bind to port %d\n", PORT);
        return 1;
    }

    if(listen(server_fd, 1)<0) {
        printf("Error: couldn't listen on port %d\n", PORT);
        return 1;
    }

    printf("Server listening on port %d\n", PORT);


    while(1) {
        int client_fd = accept(server_fd,NULL,NULL);
        if(client_fd<0) {
            printf("Error: couldn't accept connection\n");
            continue;
        }

        SSL *ssl = SSL_new(ctx);
        SSL_set_fd(ssl, client_fd);

        if(SSL_accept(ssl)<=0) {
            printf("Handshake failed\n");
            ERR_print_errors_fp(stderr);
        } else {
            printf("Handshake successful\n");
        }

        SSL_shutdown(ssl);
        SSL_free(ssl);
        close(client_fd);
    }


    SSL_CTX_free(ctx);
    OSSL_PROVIDER_unload(oqs_provider);
    OSSL_PROVIDER_unload(default_provider);
    return 0;
}