#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/provider.h>
#include <time.h>


double get_time_ms() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000.0 + ts.tv_nsec / 1000000.0;
}

int main(int argc, char *argv[]) {
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
    SSL_CTX *ctx = SSL_CTX_new(TLS_client_method());
    if(ctx == NULL) {
        printf("Error: couldn't create SSL_CTX\n");
        return 1;
    }

    SSL_CTX_set_verify(ctx, SSL_VERIFY_NONE, NULL);

    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if(sock<0) {
        printf("Error: couldn't create socket\n");
        return 1;
    }


    const char *server_ip = (argc >= 2) ? argv[1] : "127.0.0.1";

    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(4433);
    inet_pton(AF_INET, server_ip, &addr.sin_addr);            // pton - presentation to network

    if(connect(sock, (struct sockaddr*)&addr, sizeof(addr))<0) {
        printf("Error: couldn't connect to the server\n");
        return 1;
    }

    

    // Calculating the time taken for the TLS handshake
    SSL *ssl = SSL_new(ctx);
    SSL_set_fd(ssl, sock);

    double start = get_time_ms();
    int ret = SSL_connect(ssl);
    double end = get_time_ms();


    if(ret > 0) {
        BIO *wbio = SSL_get_wbio(ssl);
        BIO *rbio = SSL_get_rbio(ssl);

        long long bytes_sent = BIO_number_written(wbio);
        long long bytes_read = BIO_number_read(rbio);

        printf("DATA:%.2f,%lld,%lld\n", (end - start), bytes_sent, bytes_read);
    } else {
        printf("DATA:FAIL\n");
        ERR_print_errors_fp(stderr);
    }


    SSL_shutdown(ssl);
    SSL_free(ssl);
    close(sock);
    SSL_CTX_free(ctx);
    OSSL_PROVIDER_unload(oqs_provider);
    OSSL_PROVIDER_unload(default_provider);

    return 0;
}