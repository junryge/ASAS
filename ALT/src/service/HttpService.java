// REST API
public class HttpService {
    private static final Logger logger = LoggerFactory.getLogger(HttpService.class);
    private static final Gson gson = new Gson();
    private static final Type MAP_TYPE = new ParameterizedType() {
        @Override
        @NonNull
        public Type[] getActualTypeArguments() {
            return new Type[]{String.class, Object.class};
        }

        @Override
        @NonNull
        public Type getRawType() {
            return Map.class;
        }

        @Override
        public Type getOwnerType() {
            return null;
        }
    };

    public HttpService() {}

    /**
     * POST Synchronous Request
     * @param url request url
     * @param payload body
     * @param header encode, authorization etc
     * @return response data
     */
    public static Map<String, Object> post(
            String url,
            Map<String, Object> payload,
            Map<String, Object> header
    ) {
        return post(url, payload, header, 10, false);
    }

    /**
     * POST Asynchronous Request
     * @param url request url
     * @param payload body
     * @param header encode, authorization etc
     * @return response data
     */
    public static Map<String, Object> asyncPost(
            String url,
            Map<String, Object> payload,
            Map<String, Object> header
    ) {
        return post(url, payload, header, 10, true);
    }

    public static Map<String, Object> post(
            String url,
            Map<String, Object> parameter,
            Map<String, Object> header,
            int timeout,
            boolean isAsynchronous
    ) {
        // #1 header 구성
        Request.Builder builder = new Request.Builder();

        if (header == null) header = new HashMap<>();

        header.put("Content-Type", "application/json; charset=utf-8");

        for (Map.Entry<String, Object> entry : header.entrySet()) {
            builder.addHeader(entry.getKey(), entry.getValue().toString());
        }
        //~#1 header 구성

        // #2 body(payload) 구성
        String jsonParameter;
        RequestBody body;

        jsonParameter = gson.toJson(parameter);
        MediaType mediaType = MediaType.parse("application/json; charset=utf-8");

        if (mediaType == null) {
            logger.error("... An error occurred in setting media type !");

            return _responseError(HttpStatus.UNSUPPORTED_MEDIA_TYPE, null);
        }

        body = RequestBody.create(mediaType, jsonParameter);
        //~#2 body(payload) 구성

        // #3 request 구성
        Request request = builder.url(url).post(body).build();
        OkHttpClient okHttpClient = _createHttpClient(timeout);

        logger.info("... Request information (POST)[timeout: {} ms] >> URL: {} / Payload: {}", okHttpClient.readTimeoutMillis(), url, jsonParameter);
        //~#3 request 구성

        logger.info("[#####] Restful(post) process completed.");

        return isAsynchronous ? _executeAsyncRequest(okHttpClient, request) : _executeRequest(okHttpClient, request);
    }

    private static OkHttpClient _createHttpClient(int timeout) {
        if (timeout > 0) {
            return new OkHttpClient.Builder()
                    .connectTimeout(timeout, TimeUnit.SECONDS)
                    .readTimeout(timeout, TimeUnit.SECONDS)
                    .build();
        }

        return new OkHttpClient();
    }

    private static Map<String, Object> _executeRequest(
            OkHttpClient okHttpClient,
            Request request
    ) {
        logger.info("[####=] Returning response for synchronization request ...");

        try (Response response = okHttpClient.newCall(request).execute()) {
            if (response.isSuccessful()) {
                return _formatResponse(response);
            } else {
                logger.warn("... Response for synchronization request is failed.");
            }
        } catch (IOException e) {
            logger.error("... An error occurred while synchronization request or response !", e);
        }

        return _responseError(HttpStatus.INTERNAL_SERVER_ERROR, "synchronous error");
    }

    private static Map<String, Object> _executeAsyncRequest(
            OkHttpClient okHttpClient,
            Request request
    ) {
        CountDownLatch latch = new CountDownLatch(1);
        List<Map<String, Object>> responses = new ArrayList<>();

        logger.info("[####=] Returning response for asynchronous request ...");

        try {
            okHttpClient.newCall(request).enqueue(new Callback() {
                @Override
                @EverythingIsNonNull
                public void onFailure(Call call, IOException e) {
                    logger.warn("... Response for asynchronous request is failed.", e);

                    responses.add(_responseError(HttpStatus.INTERNAL_SERVER_ERROR, "<asynchronous> response error"));

                    latch.countDown();
                }

                @Override
                @EverythingIsNonNull
                public void onResponse(Call call, Response response) {
                    try {
                        responses.add(_formatResponse(response));
                    } catch (Exception e) {
                        logger.error("... An error occurred while asynchronous request or response !", e);
                    } finally {
                        try {
                            latch.countDown();
                        } catch (Exception e) {
                            logger.error("... Error closing latch !", e);
                        }
                    }
                }
            });

            if (latch.await(30, TimeUnit.SECONDS) && !responses.isEmpty()) {
                logger.info("... Response for asynchronous request is successful.");

                return responses.get(0);
            }
        } catch (InterruptedException e) {
            logger.error("...An error occurred while asynchronous request or response ! - InterruptedException", e);
        } catch (Exception e) {
            logger.error("... An error occurred while asynchronous request or response !", e);
        }

        return _responseError(HttpStatus.INTERNAL_SERVER_ERROR, "asynchronous error");
    }

    private static Map<String, Object> _formatResponse(Response response) {
        Map<String, Object> result = new HashMap<>();
        ResponseBody responseBody = response.body();

        if (response.isSuccessful() && responseBody != null) {
            String responseStr = "";
            try {
                responseStr = responseBody.string();
                result = gson.fromJson(responseStr, MAP_TYPE);
            } catch (IOException e) {
                throw new RuntimeException(e);
            } finally {
                try {
                    responseBody.close();   // 응답이 끝나면 반드시 닫아야 함 ---> 소켓 리소스 낭비 및 속도 저하 방지
                } catch (Exception e) {
                    logger.error("... An error occurred closing response !", e);
                }
            }

            logger.info("... Request successful >> {}", responseStr);
        }

        return result;
    }

    private static Map<String, Object> _responseError(HttpStatus httpStatus, String comment) {
        return Map.of(
                "code", httpStatus.getCode(),
                "message", httpStatus.getMessage() + (comment == null ? "" : "/" + comment)
        );
    }

    private enum HttpStatus {
        // 4xx
        BAD_REQUEST(400, "Bad Request"),
        UNAUTHORIZED(401, "Unauthorized"),
        FORBIDDEN(403, "Forbidden"),
        NOT_FOUND(404, "Not Found"),
        METHOD_NOT_ALLOWED(405, "Method Not Allowed"),
        NOT_ACCEPTABLE(406, "Not Acceptable"),
        REQUEST_TIMEOUT(408, "Request Timeout"),
        CONFLICT(409, "Conflict"),
        GONE(410, "Gone"),
        UNSUPPORTED_MEDIA_TYPE(415, "Unsupported Media Type"),
        // 5xx
        INTERNAL_SERVER_ERROR(500, "Internal Server Error"),
        NOT_IMPLEMENTED(501, "Not Implemented"),
        BAD_GATEWAY(502, "Bad Gateway"),
        SERVICE_UNAVAILABLE(503, "Service Unavailable"),
        GATEWAY_TIMEOUT(504, "Gateway Timeout"),
        HTTP_VERSION_NOT_SUPPORTED(505, "HTTP Version Not Supported");

        private final int code;
        private final String message;

        HttpStatus(int code, String message) {
            this.code = code;
            this.message = message;
        }

        public int getCode() {
            return code;
        }

        public String getMessage() {
            return message;
        }
    }
}
