document.addEventListener("DOMContentLoaded", function () {
    // ----------------- ELEMENTS -----------------
    const postTitle = document.getElementById("postTitle");
    const postHeading = document.getElementById("postHeading");
    const postImage = document.getElementById("postImage");
    const postAuthor = document.getElementById("postAuthor");
    const postContent = document.getElementById("postContent");
    const commentCount = document.getElementById("commentCount");
    const commentsList = document.getElementById("commentsList");
    const commentForm = document.getElementById("commentForm");
    const commentText = document.getElementById("comment");
    const nameInput = document.getElementById("name");
    const emailInput = document.getElementById("email");

    const recentPostsContainer = document.getElementById("recentPosts");
    const categoryList = document.getElementById("category-list");
    const tagList = document.getElementById("tag-list");

    const searchForm = document.getElementById("blog-search-form");
    const searchInput = document.getElementById("search-input");

    const newsletterForm = document.getElementById("newsletter-form");
    const newsletterEmail = document.getElementById("newsletter-email");

    // ----------------- API URLS -----------------
    const API_BASE = "https://www.services.fixlabtech.com/api/blog/blogs/";
    const CATEGORY_URL = "https://www.services.fixlabtech.com/api/blog/categories/";
    const TAG_URL = "https://www.services.fixlabtech.com/api/blog/tags/";
    const NEWSLETTER_URL = "https://www.services.fixlabtech.com/api/blog/newsletter/subscribe/";

    const urlParams = new URLSearchParams(window.location.search);
    const postId = urlParams.get("id");
    const searchQueryFromURL = urlParams.get("search") || "";

    if (!postId) {
        Swal.fire("Error", "No blog post selected.", "error");
        return;
    }

    // ----------------- HELPERS -----------------
    function formatDate(dateStr) {
        return dateStr ? new Date(dateStr).toLocaleDateString() : "Unknown Date";
    }

    function getResults(data) {
        if (!data) return [];
        if (data.data && Array.isArray(data.data.results)) return data.data.results;
        if (data.data && Array.isArray(data.data)) return data.data;
        if (Array.isArray(data.results)) return data.results;
        if (Array.isArray(data)) return data;
        return [];
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === name + "=") {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // ----------------- FETCH SINGLE POST -----------------
    function fetchPost() {
        fetch(`${API_BASE}${postId}/`)
            .then(res => res.json())
            .then(resp => {
                const blog = resp.data;
                if (!blog) {
                    Swal.fire("Error", "Post not found.", "error");
                    return;
                }

                postTitle.textContent = blog.title || "No Title";
                postHeading.textContent = blog.title || "No Title";
                postImage.src = blog.image || "assets/img/blog/default.jpg";
                postAuthor.textContent = blog.author || "Unknown";

                // ✅ Insert excerpt in the middle of content
                let content = blog.content || "No content available.";
                let words = content.split(" ");
                let middleIndex = Math.floor(words.length / 2);

                let firstHalf = words.slice(0, middleIndex).join(" ");
                let secondHalf = words.slice(middleIndex).join(" ");

                postContent.innerHTML = `
                    <p>${firstHalf}</p>
                    ${blog.excerpt ? `
                        <div class="quote-wrapper">
                            <div class="quotes">${blog.excerpt}</div>
                        </div>
                    ` : ""}
                    <p>${secondHalf}</p>
                `;

                loadComments(blog.comments || []);

                // Load tags
                if (tagList) {
                    tagList.innerHTML = "";
                    const tags = blog.tags || [];
                    if (!tags.length) {
                        tagList.innerHTML = "<li>No tags found.</li>";
                    } else {
                        tags.forEach(tag => {
                            tagList.innerHTML += `<li><a href="#">${tag.name}</a></li>`;
                        });
                    }
                }
            })
            .catch(() => Swal.fire("Error", "Failed to load blog post.", "error"));
    }

    function loadComments(comments) {
        commentsList.innerHTML = "";
        if (!comments.length) {
            commentsList.innerHTML = "<p>No comments yet. Be the first!</p>";
            commentCount.textContent = "0 Comments";
            return;
        }

        comments.forEach(c => {
            const div = document.createElement("div");
            div.classList.add("comment-list");
            div.innerHTML = `
                <div class="single-comment justify-content-between d-flex">
                    <div class="user justify-content-between d-flex">
                        <div class="desc">
                            <p class="comment">${c.content}</p>
                            <div class="d-flex justify-content-between">
                                <div class="d-flex align-items-center">
                                    <h5><a href="#">${c.name || "Anonymous"}</a></h5>
                                    <p class="date">${formatDate(c.created_at)}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>`;
            commentsList.appendChild(div);
        });
        commentCount.textContent = `${comments.length} Comments`;
    }

    // ----------------- SUBMIT COMMENT -----------------
    if (commentForm) {
        commentForm.addEventListener("submit", function (e) {
            e.preventDefault();
            const name = nameInput.value.trim();
            const email = emailInput.value.trim();
            const comment = commentText.value.trim();

            if (!name || !email || !comment) {
                Swal.fire("Warning", "All fields are required!", "warning");
                return;
            }

            fetch(`${API_BASE}${postId}/comments/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken")
                },
                body: JSON.stringify({ post: postId, name, email, content: comment })
            })
            .then(res => res.json())
            .then(() => {
                Swal.fire("Success", "Comment posted successfully!", "success");
                commentForm.reset();
                fetchPost();
            })
            .catch(() => Swal.fire("Error", "Failed to post comment.", "error"));
        });
    }

    // ----------------- FETCH RECENT POSTS -----------------
    function fetchRecentPosts() {
        fetch(API_BASE)
            .then(res => res.json())
            .then(resp => {
                const posts = getResults(resp);
                recentPostsContainer.innerHTML = "";
                posts.slice(0, 5).forEach(post => {
                    recentPostsContainer.innerHTML += `
                        <div class="media post_item">
                            <img src="${post.image || 'assets/img/blog/default.jpg'}" alt="${post.title}" width="80">
                            <div class="media-body">
                                <a href="blog_details.html?id=${post.id}">
                                    <h3>${post.title}</h3>
                                </a>
                                <p>${formatDate(post.created_at)}</p>
                            </div>
                        </div>`;
                });
            })
            .catch(() => console.error("Recent posts fetch error"));
    }

    // ----------------- FETCH CATEGORIES -----------------
    function fetchCategories() {
        if (!categoryList) return;
        fetch(CATEGORY_URL)
            .then(res => res.json())
            .then(resp => {
                const categories = resp.data || [];
                categoryList.innerHTML = "";
                categories.forEach(cat => {
                    categoryList.innerHTML += `<li><a href="#">${cat.name} (${cat.blog_count || 0})</a></li>`;
                });
            })
            .catch(() => console.error("Category fetch error"));
    }

    // ----------------- FETCH TAGS -----------------
    function fetchTags() {
        if (!tagList) return;
        fetch(TAG_URL)
            .then(res => res.json())
            .then(resp => {
                const tags = resp.data || resp.results || [];
                tagList.innerHTML = "";
                if (!tags.length) {
                    tagList.innerHTML = "<li>No tags found.</li>";
                    return;
                }
                tags.forEach(tag => {
                    tagList.innerHTML += `<li><a href="#">${tag.name}</a></li>`;
                });
            })
            .catch(() => tagList.innerHTML = "<li>Error loading tags.</li>");
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

            fetch(NEWSLETTER_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken")
                },
                body: JSON.stringify({ email })
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
            .catch(() => Swal.fire("Error", "Unable to subscribe at the moment.", "error"));
        });
    }

    // ----------------- SEARCH -----------------
    if (searchForm) {
        if (searchQueryFromURL && searchInput) {
            searchInput.value = searchQueryFromURL;
        }

        searchForm.addEventListener("submit", function (e) {
            e.preventDefault();
            const query = searchInput.value.trim();
            if (!query) return;
            window.location.href = `blog.html?search=${encodeURIComponent(query)}`;
        });
    }

    // ----------------- INIT -----------------
    fetchPost();
    fetchRecentPosts();
    fetchCategories();
    fetchTags();
});
