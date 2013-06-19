/*
 * cloudletcachefs - cloudlet cachcing emulation fs
 *
 * copyright (c) 2006-2012 carnegie mellon university
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

#include <sys/types.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <poll.h>
#include <errno.h>
#define FUSE_USE_VERSION 26
#include <fuse.h>
#include "cachefs-private.h"


#define DEBUG_FUSE
#ifdef DEBUG_FUSE
#define DPRINTF(fmt, ...) \
    do { \
    	fprintf(stdout, "[DEBUG][fuse] " fmt, ## __VA_ARGS__); \
    	fprintf(stdout, "\n"); fflush(stdout); \
    } while (0) 
#else
#define DPRINTF(fmt, ...) \
    do { } while (0)
#endif

static const char *hello_str = "Hello World!\n";
static const char *hello_path = "/hello";

/* internal utility methods */
static bool parse_stinfo(const char *buf, bool *is_local, struct stat *stbuf)
{
	gchar *st_key;
	guint64 st_value = -1;

    gchar **components;
    gchar **cur;
	gchar *end;
	components = g_strsplit(buf, ",", 0);
	if (!components){
		return false;
	}

	for (cur = components; *cur != NULL; cur++) {
		gchar **each_stinfo= g_strsplit(*cur, ":", 0);
		if ((*each_stinfo == NULL) || (*(each_stinfo+1) == NULL)){
			return false;
		}
		st_key = *(each_stinfo+0);
		st_value = g_ascii_strtoull(*(each_stinfo+1), &end, 10);
		if (*(each_stinfo+1) == end) {
			// string conversion failed
			return false;
		}
		if (strcmp(st_key, "atime") == 0){
			stbuf->st_atime = st_value;
		} else if (strcmp(st_key, "ctime") == 0){
			stbuf->st_ctime = st_value;
		} else if (strcmp(st_key, "mtime") == 0){
			stbuf->st_mtime = st_value;
		} else if (strcmp(st_key, "mode") == 0){
			stbuf->st_mode = st_value;
		} else if (strcmp(st_key, "gid") == 0){
			stbuf->st_gid = st_value;
		} else if (strcmp(st_key, "uid") == 0){
			stbuf->st_uid = st_value;
		} else if (strcmp(st_key, "nlink") == 0){
			stbuf->st_nlink= st_value;
		} else if (strcmp(st_key, "size") == 0){
			stbuf->st_size = st_value;
		} else if (strcmp(st_key, "exists") == 0){
			*is_local = st_value;
		} else {
			return false;
		}
		g_strfreev(each_stinfo);
	}
    g_strfreev(components);
    return true;
}

extern const char *URL_ROOT;
static char* convert_to_relpath(const char* path)
{
	int url_root_len = strlen(URL_ROOT);
	char *rel_path = (char*)malloc(strlen(path)+url_root_len+1);
	rel_path[strlen(path)+url_root_len] = '\0';
	if (strcmp(path, "/") == 0){
		// remove '/'
		memset(rel_path, '\0', strlen(path)+url_root_len+1);
		memcpy(rel_path, URL_ROOT, url_root_len);
	}else{
		memcpy(rel_path, URL_ROOT, url_root_len);
		memcpy(rel_path+url_root_len, path, strlen(path));
	}

	return rel_path;
}


/* FUSE operation */

static int do_getattr(const char *path, struct stat *stbuf)
{
	int res = 0;
	char *ret_buf = NULL;
	char* rel_path = convert_to_relpath(path);

	memset(stbuf, 0, sizeof(struct stat));
	DPRINTF("request getattr : %s (%s)", path, rel_path);
	if (_redis_get_attr(rel_path, &ret_buf) != EXIT_SUCCESS){
		return -ENOENT;
	}
	if (ret_buf == NULL){
		return -ENOENT;
	}

	DPRINTF("ret getattr : %s --> %s", rel_path, ret_buf);
	bool is_local = false;
	if (!parse_stinfo(ret_buf, &is_local, stbuf)){
		return -ENOENT;
	}

	if (is_local){
		// cached 
		free(ret_buf);
		return res;
	}else{
		// Need to fetch
		// TO BE IMPLEMENTED
	}
}

static int do_readdir(const char *path, void *buf, fuse_fill_dir_t filler,
		off_t offset, struct fuse_file_info *fi)
{
	int i = 0;
	(void) offset;
	(void) fi;

	char* rel_path = convert_to_relpath(path);
    DPRINTF("readdir : %s", rel_path);
	filler(buf, ".", NULL, 0);
	filler(buf, "..", NULL, 0);

    GSList *dirlist = NULL;
    if(_redis_get_readdir(rel_path, &dirlist) == EXIT_SUCCESS){
		for(i = 0; i < g_slist_length(dirlist); i++){
			gpointer dirname = g_slist_nth_data(dirlist, i);
			DPRINTF("readir : %s", (char *)dirname);
			filler(buf, dirname, NULL, 0);
		}
		g_slist_free(dirlist);
	}else{
    	DPRINTF("FAILED");
    	free(rel_path);
    	return -ENOENT;
	}

	free(rel_path);
	return 0;
}

static int do_open(const char *path, struct fuse_file_info *fi)
{
	if(strcmp(path, hello_path) != 0)
		return -ENOENT;

	if((fi->flags & 3) != O_RDONLY)
		return -EACCES;

	return 0;
}

static int do_read(const char *path, char *buf, size_t size, off_t offset,
		struct fuse_file_info *fi)
{
	size_t len;
	(void) fi;
	if(strcmp(path, hello_path) != 0)
		return -ENOENT;

	len = strlen(hello_str);
	if (offset < len) {
		if (offset + size > len)
			size = len - offset;
		memcpy(buf, hello_str + offset, size);
	} else
		size = 0;

	return size;
}

static const struct fuse_operations fuse_ops = {
    .getattr = do_getattr,
    .readdir = do_readdir,
    .open = do_open,
    .read = do_read,
    .flag_nullpath_ok = 1,
};


/* FUSE operation */
void _cachefs_fuse_new(struct cachefs *fs, GError **err)
{
	// TODO: clean-up error message
    GPtrArray *argv;
    struct fuse_args args;

    /* Construct mountpoint */
    fs->mountpoint = g_strdup("/var/tmp/cloudlet-cachefs-XXXXXX");
    if (mkdtemp(fs->mountpoint) == NULL) {
        //g_set_error(err, VMNETFS_FUSE_ERROR,
        //        VMNETFS_FUSE_ERROR_BAD_MOUNTPOINT,
        //        "Could not create mountpoint: %s", strerror(errno));
        goto bad_dealloc;
    }

    /* validate cache directory for a given URI */
    fs->uri_root = g_strdup(URL_ROOT);

    /* Build FUSE command line */
    argv = g_ptr_array_new();
    g_ptr_array_add(argv, g_strdup("-odefault_permissions"));
	//g_ptr_array_add(argv, g_strdup("-oallow_root"));
    g_ptr_array_add(argv, g_strdup_printf("-ofsname=cachefs#%d", getpid()));
    g_ptr_array_add(argv, g_strdup("-osubtype=cachefs"));
    g_ptr_array_add(argv, g_strdup("-obig_writes"));
    g_ptr_array_add(argv, g_strdup("-ointr"));
    /* Avoid kernel page cache in order to preserve semantics of read()
       and write() return values. */
    g_ptr_array_add(argv, g_strdup("-odirect_io"));
    g_ptr_array_add(argv, NULL);
    args.argv = (gchar **) g_ptr_array_free(argv, FALSE);
    args.argc = g_strv_length(args.argv);
    args.allocated = 0;

    /* Initialize FUSE */
    fs->chan = fuse_mount(fs->mountpoint, &args);
    if (fs->chan == NULL) {
        //g_set_error(err, VMNETFS_FUSE_ERROR, VMNETFS_FUSE_ERROR_FAILED,
        //        "Couldn't mount FUSE filesystem");
        //g_strfreev(args.argv);
        goto bad_rmdir;
    }
    fs->fuse = fuse_new(fs->chan, &args, &fuse_ops, sizeof(fuse_ops), NULL);
    g_strfreev(args.argv);
    if (fs->fuse == NULL) {
        //g_set_error(err, VMNETFS_FUSE_ERROR, VMNETFS_FUSE_ERROR_FAILED,
        //        "Couldn't create FUSE filesystem");
        goto bad_unmount;
    }

    return;

bad_unmount:
    fuse_unmount(fs->mountpoint, fs->chan);
bad_rmdir:
    rmdir(fs->mountpoint);
bad_dealloc:
    g_free(fs->mountpoint);
    return;
}

void _cachefs_fuse_run(struct cachefs *fs)
{
    fuse_loop_mt(fs->fuse);
}

void _cachefs_fuse_terminate(struct cachefs *fs)
{
    char *argv[] = {"fusermount", "-uqz", "--", fs->mountpoint, NULL};

    /* swallow errors */
    g_spawn_sync("/", argv, NULL, G_SPAWN_SEARCH_PATH, NULL, NULL, NULL,
            NULL, NULL, NULL);
}

void _cachefs_fuse_free(struct cachefs *fs)
{
    if (fs->fuse == NULL) {
        return;
    }

    /* Normally the filesystem will already have been unmounted.  Try
       to make sure. */
    fuse_unmount(fs->mountpoint, fs->chan);
    fuse_destroy(fs->fuse);
    rmdir(fs->mountpoint);
    g_free(fs->mountpoint);
}

