package generators;

import java.util.List;

import model.tree.Node;

public interface NodeGenerator {

	public Node generateNode();
	public List<Node> generateNodes();
}
