// Create a new QWebChannel and connect to the bridge object
new QWebChannel(qt.webChannelTransport, function(channel) {
    var bridge = channel.objects.bridge;

    // You can now call Python methods from JavaScript
    bridge.receiveMessageFromJs("Hello from JavaScript!");

    // And receive data from Python
    console.log(bridge.sendMessageToJs());
});





//
//
//document.addEventListener("DOMContentLoaded", function() {
//  // Select the element
//  var typicalLevelupRow = document.getElementById("typical_levelup_row");
//
//  // Add click event listener
//  typicalLevelupRow.addEventListener("click", function() {
//
//    // Example: Add a new row below
//    var newRow = document.createElement("tr");
//    newRow.innerHTML = "<th>New Stat:</th><td>New Value</td>";
//
//    // Append the new row to the table
//    typicalLevelupRow.parentNode.insertBefore(newRow, typicalLevelupRow.nextSibling);
//  });
//});
