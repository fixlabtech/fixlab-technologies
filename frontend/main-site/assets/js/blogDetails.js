document.addEventListener("DOMContentLoaded", function () {
    const postTitle = document.getElementById("postTitle");
    const postHeading = document.getElementById("postHeading");
    const postImage = document.getElementById("postImage");
    const postAuthor = document.getElementById("postAuthor");
    const postContent = document.getElementById("postContent");
    const commentCount = document.getElementById("commentCount");
    const commentsList = document.getElementById("commentsList");
    const commentForm = document.getElementById("commentForm");
    const recentPostsContainer = document.getElementById("recentPosts");

    const urlParams = new URLSearchParams(window.location.search);
    const postId = urlParams.get("id");

    if (!postId) {
        Swal.fire("Error", "No blog post selected.", "error");
        return;
    }

    const API_BASE = "http://127.0.0.1:8000/api/blog/blogs/";

    // ----------------- HELPER -----------------
    function getResults(data) {
        if (!data) return [];
        if (data.data && Array.isArray(data.data.results)) return data.data.results; // pagination
        if (data.data && Array.isArray(data.data)) return data.data; // normal array
        if (Array.isArray(data.results)) return data.results;
        if (Array.isArray(data)) return data;
        return [];
    }

    function formatDate(dateStr) {
        return dateStr ? new Date(dateStr).toLocaleDateString() : "Unknown Date";
    }

    // ----------------- FETCH SINGLE POST -----------------
    fetch(`${API_BASE}${postId}/`)
        .then(res => res.json())
        .then(resp => {
            const blog = resp.data;

            postTitle.textContent = blog.title || "No Title";
            postHeading.textContent = blog.title || "No Title";
            postImage.src = blog.image || "assets/img/blog/default.jpg";
            postAuthor.textContent = blog.author || "Unknown";
            postContent.textContent = blog.content || "No content available.";

            const comments = blog.comments || [];
            commentsList.innerHTML = "";
            if (!comments.length) {
                commentsList.innerHTML = "<p>No comments yet. Be the first!</p>";
                commentCount.textContent = "0 Comments";
            } else {
                comments.forEach(c => {
                    const div = document.createElement("div");
                    div.classList.add("comment-list");
                    div.innerHTML = `
                        <div class="single-comment justify-content-between d-flex">
                            <div class="user justify-content-between d-flex">
                                <div class="thumb">
                                    <img src="assets/img/blog/comment.png" alt="commenter">
                                </div>
                                <div class="desc">
                                    <p class="comment">${c.content}</p>
                                    <div class="d-flex justify-content-between">
                                        <div class="d-flex align-items-center">
                                            <h5><a href="#">${c.name}</a></h5>
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
        })
        .catch(err => Swal.fire("Error", err.message, "error"));

    // ----------------- SUBMIT COMMENT -----------------
    commentForm.addEventListener("submit", function (e) {
        e.preventDefault();
        const name = document.getElementById("name").value.trim();
        const email = document.getElementById("email").value.trim();
        const comment = document.getElementById("comment").value.trim();

        if (!name || !email || !comment) {
            Swal.fire("Validation Error", "All fields are required!", "warning");
            return;
        }

        fetch(`${API_BASE}${postId}/comments/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken")
            },
            body: JSON.stringify({
                post: postId,
                name: name,
                email: email,
                content: comment
            })
        })
        .then(res => {
            if (!res.ok) throw new Error("Failed to post comment");
            return res.json();
        })
        .then(() => {
            Swal.fire("Success", "Comment posted successfully!", "success");
            commentForm.reset();

            // Refresh comments
            fetch(`${API_BASE}${postId}/`)
                .then(res => res.json())
                .then(resp => {
                    const comments = resp.data.comments || [];
                    commentsList.innerHTML = "";
                    comments.forEach(c => {
                        const div = document.createElement("div");
                        div.classList.add("comment-list");
                        div.innerHTML = `
                            <div class="single-comment justify-content-between d-flex">
                                <div class="user justify-content-between d-flex">
                                    <div class="thumb">
                                        <img src="assets/img/blog/comment.png" alt="commenter">
                                    </div>
                                    <div class="desc">
                                        <p class="comment">${c.content}</p>
                                        <div class="d-flex justify-content-between">
                                            <div class="d-flex align-items-center">
                                                <h5><a href="#">${c.name}</a></h5>
                                                <p class="date">${formatDate(c.created_at)}</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>`;
                        commentsList.appendChild(div);
                    });
                    commentCount.textContent = `${comments.length} Comments`;
                });
        })
        .catch(err => Swal.fire("Error", err.message, "error"));
    });

    // ----------------- RECENT POSTS -----------------
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
        .catch(err => Swal.fire("Error", err.message, "error"));

    // ----------------- HELPER: CSRF -----------------
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
});
