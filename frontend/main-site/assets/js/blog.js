document.addEventListener("DOMContentLoaded", function () {
    const blogPostsContainer = document.getElementById("blog-posts-container");
    const pagination = document.getElementById("pagination");
    const categoryList = document.getElementById("category-list");
    const recentPosts = document.getElementById("recent-posts");
    const tagList = document.getElementById("tag-list");
    const searchForm = document.getElementById("blog-search-form");
    const searchInput = document.getElementById("search-input");
    const newsletterForm = document.getElementById("newsletter-form");
    const newsletterEmail = document.getElementById("newsletter-email");

    // ✅ Django API base URLs
    const apiBaseUrl = "https://www.services.fixlabtech.com/api/blog/blogs/";
    const categoryUrl = "https://www.services.fixlabtech.com/api/blog/categories/";
    const tagUrl = "https://www.services.fixlabtech.com/api/blog/tags/";
    const newsletterUrl = "https://www.services.fixlabtech.com/api/blog/newsletter/subscribe/";

    // ----------------- HELPERS -----------------
    function getResults(data) {
        if (!data) return [];
        if (data.data && Array.isArray(data.data.results)) return data.data.results;
        if (data.data && Array.isArray(data.data)) return data.data;
        if (Array.isArray(data.results)) return data.results;
        if (Array.isArray(data)) return data;
        return [];
    }

    function getPaginationData(data) {
        if (!data) return {};
        return data.data || data;
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + "=")) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // ----------------- BLOG FUNCTIONS -----------------
    const urlParams = new URLSearchParams(window.location.search);
    const searchQueryFromURL = urlParams.get("search") || "";

    let currentQuery = "";

    function fetchBlogs(page = 1, query = "", category = "", tag = "") {
        currentQuery = query || "";
        let url = `${apiBaseUrl}?page=${page}`;
        if (query) url += `&search=${encodeURIComponent(query)}`;
        if (category) url += `&category=${category}`;
        if (tag) url += `&tag=${tag}`;

        fetch(url)
            .then(res => {
                if (!res.ok) throw new Error("Failed to fetch blogs");
                return res.json();
            })
            .then(data => {
                const blogs = getResults(data);
                renderBlogs(blogs, query);
                renderPagination(getPaginationData(data), page, query);
            })
            .catch(err => {
                console.error("Blog fetch error:", err);
                Swal.fire("Error", "Unable to load blogs. Please try again later.", "error");
            });
    }

    function renderBlogs(blogs, query) {
        blogPostsContainer.innerHTML = "";
        if (!blogs.length) {
            blogPostsContainer.innerHTML = `<p class="text-center">No blog posts found${query ? ` for "${query}"` : ""}</p>`;
            return;
        }

        blogs.forEach(blog => {
            const postHTML = `
                <article class="blog_item">
                    <div class="blog_item_img">
                        <a href="blog_details.html?id=${blog.id}">
                            <img class="card-img rounded-0" src="${blog.image || 'assets/img/blog/default.jpg'}" alt="${blog.title}">
                        </a>
                        <a href="#" class="blog_item_date">
                            <h3>${new Date(blog.created_at).getDate()}</h3>
                            <p>${new Date(blog.created_at).toLocaleString("default", { month: "short" })}</p>
                        </a>
                    </div>
                    <div class="blog_details">
                        <a class="d-inline-block" href="blog_details.html?id=${blog.id}">
                            <h2>${blog.title}</h2>
                        </a>
                        <p>${(blog.content || "").substring(0, 150)}...</p>
                        <ul class="blog-info-link">
                            <li><i class="fa fa-user"></i> ${blog.author || "Unknown"}</li>
                            <p><i class="fa fa-comments"></i> ${blog.comments_count || 0} Comments</p>
                        </ul>
                    </div>
                </article>
            `;
            blogPostsContainer.insertAdjacentHTML("beforeend", postHTML);
        });
    }

    function renderPagination(data, currentPage, query) {
        pagination.innerHTML = "";
        if (!data.count) return;

        if (data.previous) {
            pagination.innerHTML += `<li class="page-item"><a href="#" class="page-link" data-page="${currentPage - 1}" data-query="${encodeURIComponent(query || "")}">Prev</a></li>`;
        }

        pagination.innerHTML += `<li class="page-item active"><a href="#" class="page-link">${currentPage}</a></li>`;

        if (data.next) {
            pagination.innerHTML += `<li class="page-item"><a href="#" class="page-link" data-page="${currentPage + 1}" data-query="${encodeURIComponent(query || "")}">Next</a></li>`;
        }

        document.querySelectorAll("#pagination .page-link").forEach(link => {
            link.addEventListener("click", function (e) {
                e.preventDefault();
                const page = parseInt(this.dataset.page);
                const q = this.dataset.query ? decodeURIComponent(this.dataset.query) : "";
                if (page) fetchBlogs(page, q);
            });
        });
    }

    // ----------------- CATEGORIES -----------------
    function fetchCategories() {
        fetch(categoryUrl)
            .then(res => res.json())
            .then(data => {
                const categories = getResults(data);
                categoryList.innerHTML = "";
                categories.forEach(cat => {
                    categoryList.innerHTML += `
                        <li>
                            <a href="#" data-category="${cat.id}" class="d-flex">
                                <p>${cat.name}</p>
                                <p>(${cat.blog_count || 0})</p>
                            </a>
                        </li>
                    `;
                });

                categoryList.querySelectorAll("a").forEach(link => {
                    link.addEventListener("click", function (e) {
                        e.preventDefault();
                        const catId = this.dataset.category;
                        if (catId) fetchBlogs(1, "", catId);
                    });
                });
            })
            .catch(err => {
                console.error("Category fetch error:", err);
                Swal.fire("Error", "Unable to load categories", "error");
            });
    }

    // ----------------- RECENT POSTS -----------------
    function fetchRecentPosts() {
        fetch(`${apiBaseUrl}?page=1`)
            .then(res => res.json())
            .then(data => {
                const posts = getResults(data);
                recentPosts.innerHTML = "";

                if (!posts.length) {
                    recentPosts.innerHTML = `<p>No recent posts.</p>`;
                    return;
                }

                posts.slice(0, 5).forEach(post => {
                    recentPosts.innerHTML += `
                        <div class="media post_item">
                            <img src="${post.image || 'assets/img/blog/default.jpg'}" alt="${post.title}" width="80">
                            <div class="media-body">
                                <a href="blog_details.html?id=${post.id}">
                                    <h3>${post.title}</h3>
                                </a>
                                <p>${new Date(post.created_at).toLocaleDateString()}</p>
                            </div>
                        </div>
                    `;
                });
            })
            .catch(err => {
                console.error("Recent posts fetch error:", err);
                Swal.fire("Error", "Unable to load recent posts", "error");
            });
    }

    // ----------------- TAGS -----------------
    function fetchTags() {
        fetch(tagUrl)
            .then(res => res.json())
            .then(data => {
                const tags = getResults(data);
                tagList.innerHTML = "";
                tags.forEach(tag => {
                    tagList.innerHTML += `<li><a href="#" data-tag="${tag.name}">${tag.name}</a></li>`;
                });

                // ✅ Clicking a tag behaves like a search
                tagList.querySelectorAll("a").forEach(link => {
                    link.addEventListener("click", function (e) {
                        e.preventDefault();
                        const tagName = this.dataset.tag;
                        searchInput.value = tagName;
                        fetchBlogs(1, tagName);
                        // Clear URL param so refresh won’t repeat search
                        window.history.replaceState({}, document.title, window.location.pathname);
                    });
                });
            })
            .catch(err => {
                console.error("Tags fetch error:", err);
                Swal.fire("Error", "Unable to load tags", "error");
            });
    }

    // ----------------- SEARCH -----------------
    if (searchForm && searchInput) {
        let handledURLSearch = false;

        searchInput.addEventListener("input", function () {
            if (handledURLSearch) {
                handledURLSearch = false;
                return;
            }
            const query = searchInput.value.trim();
            if (query) {
                fetchBlogs(1, query);
            } else {
                window.history.replaceState({}, document.title, window.location.pathname);
                fetchBlogs();
            }
        });

        searchForm.addEventListener("submit", function (e) {
            e.preventDefault();
            const query = searchInput.value.trim();
            if (query) {
                window.location.href = `blog.html?search=${encodeURIComponent(query)}`;
            } else {
                window.history.replaceState({}, document.title, window.location.pathname);
                fetchBlogs();
            }
        });

        if (searchQueryFromURL) {
            searchInput.value = searchQueryFromURL;
            fetchBlogs(1, searchQueryFromURL);
            handledURLSearch = true;
            window.history.replaceState({}, document.title, window.location.pathname);
        } else {
            fetchBlogs();
        }
    }

    // ----------------- NEWSLETTER -----------------
    if (newsletterForm) {
        newsletterForm.addEventListener("submit", function (e) {
            e.preventDefault();
            const email = newsletterEmail.value.trim();

            if (!email) {
                Swal.fire("Warning", "Please enter a valid email", "warning");
                return;
            }

            fetch(newsletterUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken")
                },
                body: JSON.stringify({ email: email })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === "exists") {
                    Swal.fire("Info", data.message, "info");
                } else if (data.status === "subscribed") {
                    Swal.fire("Success", data.message, "success");
                    newsletterForm.reset();
                } else {
                    Swal.fire("Error", "Something went wrong. Please try again.", "error");
                }
            })
            .catch(() => {
                Swal.fire("Error", "Unable to subscribe at the moment.", "error");
            });
        });
    }

    // ----------------- INITIAL LOAD -----------------
    fetchCategories();
    fetchRecentPosts();
    fetchTags();
});
