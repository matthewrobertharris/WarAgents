package generators;

import java.util.ArrayList;
import java.util.List;

import model.output.Defend;
import model.tree.Node;
import model.tree.Output;
import model.tree.Tree;

public class DefaultNodeGenerator implements NodeGenerator {

	@Override
	public List<Node> generateNodes() {
		List<Node> nodes = new ArrayList<Node>();
		nodes.add(generateNode());
		return nodes;
	}
	
	@Override
	public Node generateNode() {
		Node output = new Output(null, new Defend(), null);
		output.setTree(new Tree("Default", output));
		return output;
	}

}
