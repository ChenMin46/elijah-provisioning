/* cloudletcachefs - cloudlet cachcing emulation fs
 *
 * copyright (c) 2011-2013 carnegie mellon university
 *
 * this program is free software; you can redistribute it and/or modify it
 * under the terms of version 2 of the gnu general public license as published
 * by the free software foundation.  a copy of the gnu general public license
 * should have been distributed along with this program in the file
 * copying.
 *
 * this program is distributed in the hope that it will be useful, but
 * without any warranty; without even the implied warranty of merchantability
 * or fitness for a particular purpose.  see the gnu general public license
 * for more details.
 */

#include <string.h>
#include <stdlib.h>
#include "hiredis.h"
#include "cachefs-private.h"

#define REDIS_GET_ATTRIBUTE		"GET %s\u03b1"
#define REDIS_GET_LIST_DIR		"LRANGE %s\u03b2 0 -1"
#define REDIS_KEY_EXISTS		"EXISTS %s\u03b1"


/* Internal structure to encapsulate REDIS connection */
struct redis_handler
{
    redisContext* conn;
    GMutex *lock;
};

struct redis_handler* handle = NULL;


/* Internal methods */
bool static check_connection(){
	if ((handle != NULL) && (handle->conn != NULL)){
		return true;
	}
	return false;
}

static int check_redis_return(struct redis_handler* handle, redisReply* reply)
{
    if (reply == NULL || ((int64_t) reply) == REDIS_ERR) {
        switch(handle->conn->err) {
            case REDIS_ERR_IO:
                break;
            case REDIS_ERR_EOF:
                break;
            case REDIS_ERR_PROTOCOL:
                break;
            case REDIS_ERR_OTHER:
                break;
            default:
                break;
        };
        return EXIT_FAILURE;
    }
    
    freeReplyObject(reply);
    return EXIT_SUCCESS;
}


/* public method */
bool _redis_init(const char *address, int port)
{
    redisContext *c;
    redisReply *reply;
    handle = (struct redis_handler*) malloc(sizeof(struct redis_handler));
    if (handle) {
		struct timeval timeout = { 1, 500000 }; // 1.5 seconds
		handle->conn = redisConnectWithTimeout((char*)address, port, timeout);
		if (handle->conn == NULL || handle->conn->err) {
			if (handle->conn) {
				redisFree(handle->conn);
			}
            free(handle);
			return false;
		}

		/* PING server */
		reply = redisCommand(handle->conn, "PING");
		if ((reply == NULL) || (strlen(reply->str) <= 0)){
			return false;
		}
		freeReplyObject(reply);
	}

	handle->lock = g_mutex_new();
	return true;
}

void _redis_close()
{
    int outstanding = 0;

    if (handle) {
        if (handle->conn) {
            redisFree(handle->conn);
        }
        g_mutex_free(handle->lock);
        free(handle);
    }
}

int _redis_file_exists(const char *path, bool *is_exists)
{
	if (!check_connection())
		return EXIT_FAILURE;

    g_mutex_lock(handle->lock);
    redisReply* reply;
    reply = redisCommand(handle->conn, REDIS_KEY_EXISTS, path);
    if (reply->type == REDIS_REPLY_INTEGER){
    	if (reply->integer == 1){
    		*is_exists = true;
    	}else{
    		*is_exists = false;
		}
    }
    g_mutex_unlock(handle->lock);
    return check_redis_return(handle, reply);
}

int _redis_get_attr(const char* path, char** ret_buf)
{ 
	if (!check_connection())
		return EXIT_FAILURE;

    g_mutex_lock(handle->lock);
    redisReply* reply;
    reply = redisCommand(handle->conn, REDIS_GET_ATTRIBUTE, path);
    //_cachefs_write_debug(REDIS_GET_ATTRIBUTE, path);
    if (reply->type == REDIS_REPLY_STRING && reply->len > 0){
        *ret_buf = g_strndup(reply->str, reply->len);
    } else {
        //_cachefs_write_debug("[redis] cannot get attr from redis %s(%d)\n", path, reply->len);
    }

    g_mutex_unlock(handle->lock);
    return check_redis_return(handle, reply);
}

int _redis_get_readdir(const char* path, GSList **ret_list)
{
	if (!check_connection())
		return EXIT_FAILURE;

    g_mutex_lock(handle->lock);
    redisReply* reply;
	int i = 0;
	gchar *attr_str;
    reply = redisCommand(handle->conn, REDIS_GET_LIST_DIR, path);
    _cachefs_write_debug(REDIS_GET_LIST_DIR, path);
    if (reply->type == REDIS_REPLY_ARRAY) {
        for (i = 0; i < reply->elements; i++) {
        	attr_str = g_strndup(reply->element[i]->str, reply->element[i]->len);
        	*ret_list = g_slist_append(*ret_list, attr_str);
        }
    }else{
    	//fprintf(stderr, "no return\n");
	}
    g_mutex_unlock(handle->lock);
    return check_redis_return(handle, reply);
}
